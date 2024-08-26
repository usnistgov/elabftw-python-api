import json
import logging
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Dict, Literal, Optional, Union
from urllib.parse import urljoin

import certifi
import dotenv
from pathvalidate import sanitize_filename
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from rich.console import Console
from rich.logging import RichHandler

dotenv.load_dotenv()
c = Console()

# load certificate bundle into list of bytes
CA_BUNDLE_CONTENT = os.environ.get("***REMOVED***", None)
if CA_BUNDLE_CONTENT:
    CA_BUNDLE_CONTENT = [(i + "\n").encode() for i in CA_BUNDLE_CONTENT.split(r"\n")]

logging.basicConfig(
    level="NOTSET", 
    format="%(message)s", datefmt="[%X]", 
    handlers=[RichHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)


class ELabApi:
    """
    Represents a connection to the root ELabFTW API.

    Authenticates via API key provided at init time (though this could be changed)
    and provides simple interfaces to various API endpoints. Currently mostly read-only
    """
    api_key: str
    """An ELabFTW API key"""

    api_base_url: str
    """An ELabFTW API URL root (e.g. https://elabftw.net/api/v2/)"""

    _experiment_cache: dict
    _item_cache: dict
    _user_cache: dict

    def __init__(self, api_base_url, api_key):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self._experiment_cache = {}
        self._item_cache = {}
        self._user_cache = {}

    def api_req(
        self,
        function: str,
        endpoint: str,
        **kwargs: Optional[dict],
    ):
        """
        Make a request to the ELabFTW API.

        A helper method that wraps a function from :py:mod:`requests`, but adds a
        local certificate authority chain to validate any custom certificates.
        Will automatically retry on 500 errors
        using a strategy suggested here: https://stackoverflow.com/a/35636367.

        Parameters
        ----------
        function
            The function from the ``requests`` library to use (e.g.
            ``'GET'``, ``'POST'``, ``'PATCH'``, etc.)
        endpoint
            The API endpoint to fetch (will be appended to ``ELAB_URL`` environment variable)
        **kwargs :
            Other keyword arguments are passed along to the ``fn``

        Returns
        -------
        r : :py:class:`requests.Response`
            A requests response object

        Raises
        ------
        ValueError
            If multiple methods of authentication are provided to the function
        """

        # set up a session to retry requests as needed
        s = Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        s.mount("https://", HTTPAdapter(max_retries=retries))
        s.mount("http://", HTTPAdapter(max_retries=retries))

        if 'headers' in kwargs:
            if 'Authorization' not in kwargs['headers']:
                kwargs['headers']['Authorization'] = self.api_key
            else:
                c.warning('Found an authorization header in kwargs, so not overwriting')
        else:
            kwargs['headers'] = {
                'Authorization': self.api_key
            }

        # remove leading slash from endpoint, because it's never what you want
        if endpoint[0] == '/':
            endpoint = endpoint[1:]
        url = urljoin(self.api_base_url, endpoint)
        verify_arg = True
        with tempfile.NamedTemporaryFile() as tmp:
            if CA_BUNDLE_CONTENT:
                with Path(certifi.where()).open(mode="rb") as sys_cert:
                    lines = sys_cert.readlines()
                tmp.writelines(lines)
                tmp.writelines(CA_BUNDLE_CONTENT)
                tmp.seek(0)
                verify_arg = tmp.name
            else:
                verify_arg = False

            # remove authorization header from log output
            if 'headers' in kwargs and 'Authorization' in kwargs['headers']:
                kwargs_to_log = deepcopy(kwargs)
                kwargs_to_log['headers']['Authorization'] = "**CENSORED**"
            else: 
                kwargs_to_log = kwargs
            logger.debug(f"{function} -- {url}\n{kwargs_to_log}")
            response = s.request(
                function,
                url,
                verify=verify_arg,
                **kwargs,
            )

        return response

    def get_api_keys(self):
        return self.api_req('GET', 'apikeys').json()
    
    def get_config(self):
        return self.api_req('GET', 'config').json()
    
    def get_experiments(self) -> list[Dict]:
        exp = self.api_req('GET', 'experiments').json()
        return exp 

    def get_experiments_by_status(self, status: str) -> list[Dict]:
        exp = self.api_req(
            'GET', 
            'experiments', 
            params={'q': f'status:"{status}"'}
        ).json()
        return exp 

    def get_experiments_by_category(self, category: str) -> list[Dict]:
        exp = self.api_req(
            'GET', 
            'experiments', 
            params={'q': f'category:"{category}"'}
        ).json()
        return exp 
    
    def set_experiment_category(
        self, 
        experiment_id: int,
        category_id: Optional[int] = None, 
        category_name: Optional[str] = None
    ) -> list[Dict]:
        # get category name by interrogating API
        if category_id is None:
            # need to get category_id from API
            if category_name is None:
                raise ValueError(
                    "One of 'category_id' or 'category_name' must be provided"
                )
            # get categories for the current team and find the one that matches name
            cats = self.api_req(
                'GET', "teams/current/experiments_categories"
            ).json()
            titles = [t['title'] for t in cats]
            if category_name in titles:
                category_id = [t for t in cats if t['title'] == category_name][0]['id']
            else:
                raise ValueError(
                    f"Category \"{category_name}\" was not found in this team's "
                    "list of categories"
                )

        exp = self.api_req(
            'PATCH', 
            f'experiments/{experiment_id}', 
            json={'category': category_id}
        )
        return exp 
    
    def get_experiment(self, experiment_id: int):
        if experiment_id in self._experiment_cache:
            logger.debug(f'Returning experiment "{experiment_id}" from the cache')
            return self._experiment_cache[experiment_id]
        exp = self.api_req(
            'GET', 
            f'experiments/{experiment_id}'
        ).json()
        self._experiment_cache[experiment_id] = exp
        return exp
    
    def export_experiment(
        self,
        experiment_id: int,
        output_filename: Optional[os.PathLike] = None,
        format: str = 'pdf',
        overwrite: bool = False
    ) -> Path:
        """
        Export and download an experiment in the specified format.
        
        Allowed formats are *'csv'*, *'eln'*, *'json'*, *'qrpdf'*, *'qrpng'*, *'pdf'*,
        *'pdfa'*, *'zip'*, or *'zipa'*. If no filename/path is provided, a filename
        in the current directory will be autogenerated and returned as a ``Path``
        object. The ``overwrite`` option controls whether a file that already exists
        on disk will be overwritten.
        """
        format = format.lower()
        exp = None

        # test if this is an allowed format 
        allowed_formats = [
            'csv', 'eln', 'json', 'qrpdf', 'qrpng', 'pdf', 'pdfa', 'zip', 'zipa'
        ]
        if format not in allowed_formats:
            raise ValueError(
                f"format '{format}' not one of the allowed values: {allowed_formats}"
            )
                
        # fetch experiment once in json format to get info if filename is None
        if not output_filename:
            exp = self.get_experiment(experiment_id)
            output_filename = Path(
                sanitize_filename(exp['title'] + f" [{exp['id']}]") + f'.{format}'
            )
            if output_filename.suffix == ".qrpdf":
                output_filename = output_filename.with_suffix(".qr.pdf")
            if output_filename.suffix == ".qrpng":
                output_filename = output_filename.with_suffix(".qr.png")
            if output_filename.suffix == ".pdfa":
                output_filename = output_filename.with_suffix(".pdf")
            if output_filename.suffix == ".zipa":
                output_filename = output_filename.with_suffix(".zip")
        
        if output_filename.exists() and not overwrite:
            raise FileExistsError(
                f'"{output_filename}" already exists. Use the overwrite=True argument '
                'to force overwriting'
            )

        # if format was json, we can write now
        if format == 'json':
            if not exp:
                exp = self.get_experiment(experiment_id)
            c.log(f'Writing output to "{output_filename}" as JSON')
            with output_filename.open('w', encoding='utf8') as f:
                json.dump(exp, f, indent=2)
            return output_filename

        c.log(f'Getting experiment in "{format}" format')
        r = exp = self.api_req(
            'GET', f'experiments/{experiment_id}', params={'format': format}
        )
        # mode = 'w' if format == 'csv' else 'wb'
        # encoding = 'utf8' if format == 'csv' else None
        c.log(f'Writing output to "{output_filename}"')
        with output_filename.open('wb') as f:
            f.write(r.content)

        return output_filename
    
    def get_user(self, user_id: int):
        if user_id in self._user_cache:
            logger.debug(f'Returning user "{user_id}" from the cache')
            return self._user_cache[user_id]
        user = self.api_req(
            'GET', 
            f'users/{user_id}'
        ).json()
        self._user_cache[user_id] = user
        return user
    
    def get_item(self, item_id: int):
        if item_id in self._item_cache:
            logger.debug(f'Returning item "{item_id}" from the cache')
            return self._item_cache[item_id]
        item = self.api_req(
            'GET', 
            f'items/{item_id}'
        ).json()
        self._item_cache[item_id] = item
        return item

class TeamApi(ELabApi):
    """
    Represents a single ELabFTW Team by communicating with the REST API.

    Provides methods to get information about a team and its content. Also provides
    a few static methods to get information about other teams. Currently is read-only.
    """
    # teams: Dict[Union[int, Literal['current']], Dict]
    team: Dict
    "the dictionary/JSON returned by the ELabFTW API for this team"

    team_id: Union[int, Literal['current']]
    """
    the identifier number for this team; if 'current', this attribute will be
    overwritten with the actual integer identifier the first time the API is queried 
    """

    known_teams: Dict[int, Dict] = {}
    """
    A cache of known teams used to help limit API requests if they're unnecessary
    """
                   
    def __init__(
        self,
        api_base_url: str,
        api_key: str, 
        team_id: Union[int, Literal['current']] = 'current'
    ):
        super().__init__(api_base_url, api_key)
        self.team_id = team_id
        self.team = self.api_req('GET', f'teams/{self.team_id}').json()
        if self.team_id == 'current':
            self.team_id = self.team['id']
        TeamApi.known_teams[self.team_id] = self.team

    def get_teams(self) -> list[Dict]:
        """
        Get all teams from the API (always refreshes from API and adds to cache)
        
        https://doc.elabftw.net/api/v2/#/Teams/read-teams
        """
        teams = self.api_req('GET', 'teams').json()
        for t in teams:
            TeamApi.known_teams[t['id']] = t
        logger.debug(f"teams: {teams}")
        return teams
    
    def get_team_by_name(self, name: str) -> Optional[Dict]:
        names = [t['name'] for t in TeamApi.known_teams.values()]
        if name in names:
            logger.debug("Returning team from cache")
            team = [t for t in TeamApi.known_teams.values() if t['name'] == name][0]
            logger.debug(f"team: {team}")
            return team
        else:
            logger.debug("Fetching all teams to find team by name")
            teams = self.get_teams()
            names = [t['name'] for t in teams]
            if name in names:
                team = [t for t in teams if t['name'] == name][0]
            else:
                team = None
            logger.debug(f"team: {team}")
            return team
        
    def get_team(self, id: Union[int, Literal['current']] = 'current') -> Dict:
        """
        Get a team definition by id

        https://doc.elabftw.net/api/v2/#/Teams/read-team
        """
        # if id in self.teams:
        #     logger.debug(f'Returning team "{id}" from local cache')
        #     return self.teams[id]
        # else:
        team = self.api_req('GET', f'teams/{id}').json()
        # self.teams[id] = team
        logger.debug(f"team: {team}")
        return team
    
    def get_team_tags(self) -> list[Dict]:
        """
        Get the tags defined for this team

        https://doc.elabftw.net/api/v2/#/Team%20tags/read-team_tags
        """
        tags = self.api_req('GET', 'team_tags').json()
        logger.debug(f"tags: {tags}")
        return tags
    
    def get_team_tag(self, id) -> Optional[Dict]:
        """
        Get a specific tag defined for this team
        
        https://doc.elabftw.net/api/v2/#/Team%20tags/read-team_tag
        """
        tag = self.api_req('GET', f'team_tags/{id}').json()
        if 'code' in tag and tag['code'] == 404:
            tag = None
        logger.debug(f"tag: {tag}")
        return tag
    
    def get_experiments_categories(self) -> list[Dict]:
        """
        Get the experiments categories of a team
        
        https://doc.elabftw.net/api/v2/#/Experiments%20categories/read-team-experiments-categories
        """
        cats = self.api_req('GET', f"teams/{self.team_id}/experiments_categories").json()
        logger.debug(f"categories: {cats}")
        return cats
    
    def get_experiments_category(self, cat_id: int) -> Optional[Dict]:
        """
        Get a single experiments category of a team
        
        https://doc.elabftw.net/api/v2/#/Experiments%20categories/read-team-experiments-categories
        """
        cat = self.api_req(
            'GET',
            f"teams/{self.team_id}/experiments_categories/{cat_id}"
        ).json()
        if 'code' in cat and cat['code'] == 404:
            cat = None
        logger.debug(f"category: {cat}")
        return cat
    
    def get_experiments_category_by_name(self, cat_name: str) -> Optional[Dict]:
        """
        Get a single experiments category of a team by name
        
        https://doc.elabftw.net/api/v2/#/Experiments%20categories/read-team-experiments-categories
        """
        cats = self.api_req(
            'GET', 
            f"teams/{self.team_id}/experiments_categories"
        ).json()
        
        logger.debug(f"category: {cats}")
        return cats
    
    def get_experiments_statuses(self) -> list[Dict]:
        """
        Get the experiments statuses of a team
        
        https://doc.elabftw.net/api/v2/#/Experiments%20status/read-team-experiments-status
        """
        stats = self.api_req('GET', f"teams/{self.team_id}/experiments_status").json()
        logger.debug(f"statuses: {stats}")
        return stats
    
    def get_experiments_status(self, status_id: int) -> Optional[Dict]:
        """
        Get a single experiments status of a team
        
        https://doc.elabftw.net/api/v2/#/Experiments%20status/read-team-one-expstatus
        """
        stat = self.api_req(
            'GET',
            f"teams/{self.team_id}/experiments_status/{status_id}"
        ).json()
        if 'code' in stat and stat['code'] == 404:
            stat = None
        logger.debug(f"status: {stat}")
        return stat

    def get_experiments_status_by_title(self, title: str) -> Optional[Dict]:
        """
        Get a single experiments status of a team by its name
                """
        statuses = self.get_experiments_statuses()
        titles = [s['title'] for s in statuses]
        stat = None
        if title in titles:
            stat = [s for s in statuses if s['title'] == title][0]
        logger.debug(f"stat: {stat}")
        return stat
    
    def get_items_statuses(self) -> list[Dict]:
        """
        Get the items statuses of a team
        
        https://doc.elabftw.net/api/v2/#/Resources%20status/read-team-items-status
        """
        stats = self.api_req('GET', f"teams/{self.team_id}/items_status").json()
        logger.debug(f"statuses: {stats}")
        return stats

    def get_items_status(self, status_id: int) -> Optional[Dict]:
        """
        Get a single items status of a team
        
        https://doc.elabftw.net/api/v2/#/Resources%20status/read-team-one-resstatus
        """
        stat = self.api_req(
            'GET',
            f"teams/{self.team_id}/items_status/{status_id}"
        ).json()
        if 'code' in stat and stat['code'] == 404:
            stat = None
        logger.debug(f"status: {stat}")
        return stat

    def get_items_status_by_title(self, title: str) -> Optional[Dict]:
        """
        Get a single items status of a team by its name
        """
        statuses = self.get_items_statuses()
        titles = [s['title'] for s in statuses]
        stat = None
        if title in titles:
            stat = [s for s in statuses if s['title'] == title][0]
        logger.debug(f"stat: {stat}")
        return stat