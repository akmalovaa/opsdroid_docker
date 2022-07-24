import os
import base64
import pathlib
import typing
import logging
import sys
sys.path.append(os.path.abspath("/chatops/skills"))
from settings import settings

import gitlab
import yaml
from opsdroid.skill import Skill
from opsdroid.matchers import match_regex, match_parse
from opsdroid.message import Message


# Gitlab connection
gl = gitlab.Gitlab(settings.GITLAB_API_ADDR, private_token=settings.GITLAB_TOKEN)
project_handler: typing.Any = gl.projects.get(settings.GITLAB_PROJECT_ID)


class test(Skill):
    @match_regex(r"test")
    async def test(self, message):
        test = settings.GITLAB_CD_YAML_FILE
        await message.respond(f"Text: {test}")
        # logging.info()

    @match_regex(r"me")
    async def me(self, event):
        user_id = event.user_id
        user = event.user
        await event.respond(f"User: {user}, id: {user_id}")

    @match_parse('deploy {select}')
    async def change_deploy_mode(self, message):
        deploy_mode = message.parse_result['select']
        if deploy_mode == 'auto' or deploy_mode == 'manual':
            await message.respond(_change_deploy_mode(deploy_mode, message.user))
        elif deploy_mode == 'status':
            await message.respond(f'Current deploy status: {_get_deploy_status()}')
        else:
            await message.respond(f'Im confused. Bad desire {deploy_mode}')


class BlankLineYaml(yaml.SafeDumper):
    """ In the basic version, by default, all empty lines are erased when saving.
    This class corrects this and adds empty indents between the works """
    def write_line_break(self, data=None):
        super().write_line_break(data)

        if len(self.indents) == 1:
            super().write_line_break()


def _download_remote_file_from_gitlab(project_handler: typing.Any, original_name: str) -> typing.Optional[pathlib.Path]:
    new_location: pathlib.Path = (f'/tmp/{settings.GITLAB_CD_YAML_FILE}')
    os.makedirs(os.path.dirname(os.path.realpath(new_location)), exist_ok=True)
    try:
        with open(new_location, 'wb') as f:
            project_handler.files.raw(file_path=original_name, ref='main', streamed=True, action=f.write)
        logging.info(f"Download file: {original_name}")
        return new_location
    except:
       logging.info(f"Cant download file {original_name}")
       raise SystemExit(1)


def _get_deploy_status():
    "Get deploy current status"
    # Download file
    lock_location: typing.Optional[pathlib.Path] = _download_remote_file_from_gitlab(project_handler, settings.GITLAB_CD_YAML_FILE)
    with open(lock_location, 'r') as f:
        list_doc = yaml.safe_load(f)
        rules = list_doc["deploy"]["rules"] # must specify the destination point .yml
        return rules[0]["when"]


def _change_deploy_mode(deploy_mode: str, username:str="opsdroid") -> str:
    "Change deploy mode in yml file"
    # Download file
    lock_location: typing.Optional[pathlib.Path] = _download_remote_file_from_gitlab(project_handler, settings.GITLAB_CD_YAML_FILE)
    # Cnahge yaml file
    current_deploy_status: str = _get_deploy_status()
    with open(lock_location, 'r') as f:
        list_doc = yaml.safe_load(f)
        rules = list_doc["deploy"]["rules"] # must specify the destination point .yml
        if current_deploy_status == 'manual' and deploy_mode == 'auto':
            rules[0]["when"] = "always"
        elif current_deploy_status == 'always' and deploy_mode == 'manual':
            rules[0]["when"] = "manual"
        else:
            result = 'Gitlab deploy mode - nothing to change'
            logging.info(result)
            return result
    with open(lock_location, 'w') as f:
       f.write(yaml.dump(list_doc, Dumper=BlankLineYaml, sort_keys=False))
    # Git push
    project_handler.commits.create(
            {
                "branch": settings.GITLAB_BRANCH_NAME,
                "commit_message": f"{username} change deploy mode to: {deploy_mode}, by ChatOps",
                "actions": [
                    {
                        "action": "update",
                        "file_path": settings.GITLAB_CD_YAML_FILE,
                        "content": open(lock_location).read(),
                    },
                ],
            }
        )
    result = f"{username} Changed deploy mode to: {deploy_mode}"
    logging.info(result)
    return result
