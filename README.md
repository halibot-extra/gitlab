Halibot Gitlab Module
=====================

Reports changes to gitlab repositories.

Usage
-----

To install:

```
halibot fetch gitlab
```

To add to your local halibot config:

```
halibot add gitlab
```

You have to enable the webhook for your gitlab project. See [this](https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md).
You probably have to disable SSL, I didn't write any code to support it.

Only issue and merge request events are currently supported.


Example config
--------------

```json
{
  ...


  "module-instances": {
    ...

    "gitlab-example": {
      "of": "gitlab",
      "secret": "sshhhh",
      "dest": "irc0/##example",
      "events": {
        "issues": [
          "opened",
          "reopened",
          "closed"
        ],
        "merge_request": [
          "opened",
          "reopened",
          "closed"
        ]
      }
    }

    ...
  }
}
```
