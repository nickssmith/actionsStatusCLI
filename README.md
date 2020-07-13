# View the status of Github Actions for a repo in CLI

## Setup

1. Clone or download this repo
1. Follow [this](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) guide to make a personal access token. [This](https://github.com/settings/tokens) link should take you to the github settings page to create a token
1. Create the token with repo and workflow access
1. Save the token to the text file in this repo called `token.txt`
1. TODO run script to add to bashrc etc

## Requirements
 - python3

## Usage
If setup correctly, then the script will run after every `git push`

To call the script manually


# TODO LIST
 - install script?
 - do a git fetch to check for updates after running
 - check for new PRs made by actions and report them
 - save settings and access token somehwere (.config ?)