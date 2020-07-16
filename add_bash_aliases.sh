#!/usr/bin/env bash

cmd_line="python3 "$(pwd)"/actionsStatus.py"

bash_rc=~/.bashrc

echo "Making a backup of $bash_rc"
cp $bash_rc ~/.bashrc.backup

echo "Adding the command 'gitActionsStatus' to bash"
cat <<EOT >> $bash_rc

function gitActionsStatus() {
  $cmd_line
}
export -f gitActionsStatus

EOT

function add_gp {

cat <<EOT >> $1

alias gp='git push && gitActionsStatus'
EOT

}


read -p "Add command 'gp' as an alias for 'git push' that will also show actions status after pushing? (Recommended) (y/n)?" choice
case "$choice" in
  y|Y ) echo "Adding 'gp' command to bash" && add_gp $bash_rc;;
  n|N ) echo "Skipping adding 'gp' command. Dont forge to run 'gitActionsStatus' after running 'git push'";;
  * ) echo "Skipping adding 'gp' command. Dont forge to run 'gitActionsStatus' after running 'git push'";;
esac


echo "Commands have been added to the users bashrc and a backup called $bash_rc.backup has been made"
