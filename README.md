# target-actionkit

`target-actionkit` is a Singer target for ActionKit.

Build with the [Meltano Target SDK](https://sdk.meltano.com).

<!--

Developer TODO: Update the below as needed to correctly describe the install procedure. For instance, if you do not have a PyPi repo, or if you want users to directly install from your git repo, you can modify this step as appropriate.

## Installation

Install from PyPi:

```bash
pipx install target-actionkit
```

Install from GitHub:

```bash
pipx install git+https://github.com/ORG_NAME/target-actionkit.git@main
```

-->

## Configuration

### Accepted Config Options

| name | default | description |
| -----| ------- | ----------- |
| `only_upsert_empty_fields` | `false` | If true, will not overwrite existing Contact fields in ActionKit |

A full list of supported settings and capabilities for this
target is available by running:

```bash
target-actionkit --about
```

### Configure using environment variables

This Singer target will automatically import any environment variables within the working directory's
`.env` if the `--config=ENV` is provided, such that config values will be considered if a matching
environment variable is set either in the terminal context or in the `.env` file.

### Source Authentication and Authorization

<!--
Developer TODO: If your target requires special access on the destination system, or any special authentication requirements, provide those here.
-->

## Usage

You can easily run `target-actionkit` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Target Directly

```bash
target-actionkit --version
target-actionkit --help
# Test using the "Carbon Intensity" sample:
tap-carbon-intensity | target-actionkit --config /path/to/target-actionkit-config.json
```
