import uuid

from datetime import datetime

from api import ApiResource
from api.database.v2.handlers import V2ProjectHandler
from yardstick.common.utils import result_handler
from yardstick.common.utils import change_obj_to_dict
from yardstick.common import constants as consts


class V2Projects(ApiResource):

    def get(self):
        project_handler = V2ProjectHandler()
        projects = [change_obj_to_dict(p) for p in project_handler.list_all()]

        for p in projects:
            tasks = p['tasks']
            p['tasks'] = tasks.split(',') if tasks else []

        return result_handler(consts.API_SUCCESS, {'projects': projects})

    def post(self):
        return self._dispatch_post()

    def create_project(self, args):
        try:
            name = args['name']
        except KeyError:
            return result_handler(consts.API_ERROR, 'name must be provided')

        project_id = str(uuid.uuid4())
        create_time = datetime.now()
        project_handler = V2ProjectHandler()

        project_init_data = {
            'uuid': project_id,
            'name': name,
            'time': create_time
        }
        project_handler.insert(project_init_data)

        return result_handler(consts.API_SUCCESS, {'uuid': project_id})


class V2Project(ApiResource):

    def get(self, project_id):
        try:
            uuid.UUID(project_id)
        except ValueError:
            return result_handler(consts.API_ERROR, 'invalid project id')

        project_handler = V2ProjectHandler()
        try:
            project = project_handler.get_by_uuid(project_id)
        except ValueError:
            return result_handler(consts.API_ERROR, 'no such project id')

        project_info = change_obj_to_dict(project)
        tasks = project_info['tasks']
        project_info['tasks'] = tasks.split(',') if tasks else []

        return result_handler(consts.API_SUCCESS, {'project': project_info})