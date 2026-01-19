# Configuration Guide

This directory contains a template configuration file for the `target-actionkit` Singer target.

## Configuration File

Copy `config.json` to your desired location and update it with your ActionKit credentials and settings.

## Configuration Options

### Required Fields

#### `username` (string, required)
- **Description**: Your ActionKit API username
- **Example**: `"api_user"`
- **Note**: This is used for Basic Authentication with the ActionKit REST API

#### `password` (string, required)
- **Description**: Your ActionKit API password
- **Example**: `"your_secure_password"`
- **Note**: This is used for Basic Authentication with the ActionKit REST API

#### `signup_page_short_name` (string, required)
- **Description**: The short name of the ActionKit page to use for user signups
- **Example**: `"signup"` or `"join"`
- **Note**: This page must exist in your ActionKit instance. The target uses this page when creating or subscribing users to lists.

### Optional Fields

#### `hostname` (string, optional)
- **Description**: Your ActionKit instance hostname (without the `.actionkit.com` domain)
- **Example**: `"myorganization"` (for `myorganization.actionkit.com`)
- **Note**: 
  - If provided, the target will construct the base URL as `https://{hostname}.actionkit.com/rest/v1/`
  - If `full_url` is also provided, `full_url` takes precedence
  - If neither `hostname` nor `full_url` is provided, the target may fail to connect

#### `full_url` (string, optional)
- **Description**: The complete base URL for your ActionKit instance
- **Example**: `"https://myorganization.actionkit.com"`
- **Note**: 
  - This is an alternative to using `hostname`
  - If provided, the target will use this URL directly (appending `/rest/v1/` automatically)
  - Takes precedence over `hostname` if both are provided
  - Trailing slashes are automatically stripped

#### `unsubscribe_page_short_name` (string, optional)
- **Description**: The short name of the ActionKit page to use for user unsubscribes
- **Example**: `"unsubscribe"` or `"optout"`
- **Note**: 
  - This page must exist in your ActionKit instance
  - Used when a contact's `subscribe_status` is set to `"unsubscribed"`
  - If not provided, unsubscribe functionality may not work correctly

## Example Configuration

### Minimal Configuration (Required Fields Only)

```json
{
  "username": "api_user",
  "password": "secure_password",
  "signup_page_short_name": "signup"
}
```

### Full Configuration (All Fields)

```json
{
  "username": "api_user",
  "password": "secure_password",
  "hostname": "myorganization",
  "signup_page_short_name": "signup",
  "unsubscribe_page_short_name": "unsubscribe",
  "full_url": "https://myorganization.actionkit.com"
}
```

### Using Custom URL

```json
{
  "username": "api_user",
  "password": "secure_password",
  "signup_page_short_name": "signup",
  "full_url": "https://custom-domain.com"
}
```

## Environment Variables

You can also configure the target using environment variables. The target will automatically import any environment variables within the working directory's `.env` file if `--config=ENV` is provided.

Set the following environment variables:
- `USERNAME` - Your ActionKit username
- `PASSWORD` - Your ActionKit password
- `HOSTNAME` - Your ActionKit hostname (optional)
- `SIGNUP_PAGE_SHORT_NAME` - Signup page short name
- `UNSUBSCRIBE_PAGE_SHORT_NAME` - Unsubscribe page short name (optional)
- `FULL_URL` - Full ActionKit URL (optional)
