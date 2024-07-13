import io
import logging
import os
import pathlib
import typing

import gitlab
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

GITLAB_SERVER_URL: typing.Final = "..."
ROOT_DIR: typing.Final = pathlib.Path(__file__).parents[2]
VALIDATION_FOLDER_NAMES: typing.Final[list[str]] = ["presets"]
CI_PROJECT_PATH: typing.Final = os.getenv(
    "CI_PROJECT_PATH",
    "python-community/pypelines",
)
CI_PROJECT_ID: typing.Final = os.getenv("CI_PROJECT_ID")

YAML_OBJECT = YAML()
YAML_OBJECT.preserve_quotes = True

logging.basicConfig(level=logging.INFO, format="%(message)s")


def add_project_to_includes(file_contents: str) -> str:
    dictionaried_yaml: typing.Final[dict[str, str]] = YAML_OBJECT.load(file_contents)
    dictionaried_yaml["include"] = [  # type: ignore[assignment]
        {
            "project": CI_PROJECT_PATH,
            "ref": "main",
            "file": dictionaried_yaml["include"],
        },
    ]
    io_buffer = io.BytesIO()
    YAML_OBJECT.dump(dictionaried_yaml, io_buffer)
    return io_buffer.getvalue().decode("utf-8")


def main() -> None:
    private_token: typing.Final = os.getenv("...")
    gitlab_client: typing.Final = gitlab.Gitlab(
        GITLAB_SERVER_URL,
        private_token=private_token,
    )
    all_valid: bool = True

    pypelines_project: typing.Final = gitlab_client.projects.get(CI_PROJECT_ID)  # type: ignore[arg-type]

    # get GitLab token from environment variables
    for folder_to_validate in VALIDATION_FOLDER_NAMES:
        for file_name in filter(
            lambda file_name: file_name.endswith(".yml"),
            os.listdir(folder_to_validate),
        ):
            with pathlib.Path(
                f"{folder_to_validate}/{file_name}",
            ).open() as yml_file_to_validate:
                try:
                    yaml_content_with_project: typing.Final = add_project_to_includes(
                        yml_file_to_validate.read(),
                    )

                except YAMLError as e:
                    all_valid = False
                    logging.info(
                        f"{folder_to_validate}/{file_name} has syntax error\n {e}",
                    )

                else:
                    lint_result: typing.Final = pypelines_project.ci_lint.create(
                        {"content": yaml_content_with_project},
                    )
                    logging.info(
                        f"{folder_to_validate}/{file_name} is {'valid' if lint_result.valid else 'invalid'}",
                    )
                    if not lint_result.valid:
                        all_valid = False
                        logging.info(lint_result.errors)

            logging.info("\n")

    if not all_valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
