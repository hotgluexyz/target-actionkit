"""ActionKit target class."""

from singer_sdk import typing as th
from target_hotglue.target import TargetHotglue

from target_actionkit.sinks import (
    ContactsSink,
)


class TargetActionKit(TargetHotglue):
    """Target for ActionKit."""

    SINK_TYPES = [
        ContactsSink,
    ]
    name = "target-actionkit"

    def __init__(
        self,
        config=None,
        parse_env_config: bool = False,
        validate_config: bool = True,
        state: str = None,
    ) -> None:
        self.config_file = config[0]
        super().__init__(
            config=config,
            parse_env_config=parse_env_config,
            validate_config=validate_config,
        )

    config_jsonschema = th.PropertiesList(
        th.Property("username", th.StringType, required=True),
        th.Property("password", th.StringType, required=True),
        th.Property("hostname", th.StringType, required=False),
    ).to_dict()


if __name__ == "__main__":
    TargetActionKit.cli()
