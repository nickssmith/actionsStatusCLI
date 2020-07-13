#!/usr/bin/env bash

cmd_line="python3 "$(pwd)"/actionsStatus.py"

bash_rc=~/.bashrc

echo "Making a backup of $bash_rc"
cp $bash_rc ~/.bashrc.backup

cat <<EOT >> $bash_rc
function gitActionsStatus() {
  $cmd_line
}
export -f gitActionsStatus
EOT

echo "The command 'gitActionsStatus' has been added to the users bashrc"
