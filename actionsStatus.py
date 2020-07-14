import json
import os
import requests
import subprocess
import threading
import time


class actionsStatus:

    def __init__(self):
        self.access_token = None
        self.repo_owner = ""
        self.repo = ""
        # list of all workflows for the repo
        self.workflows = []

        # number of seconds between start of program and giving up if no running actions are found
        # is multiplied by number of workflows as is n seconds per workflow
        self.timeout_to_find_running_actions = 5
        self.timeout_reached = False
        self.has_running_actions = False
        self.exiting = False
        self.len_of_overwrite_output = 0

        self.set_of_completed_action_ids = set()
        self.set_of_running_action_ids = set()
        self.dict_of_failed_actions = dict()

        # load vars
        self.load_access_token()
        self.get_user_and_repo_from_cwd()

        assert self.access_token != None

    def check_for_update(self):
        script_dir = os.path.dirname(__file__)
        process = subprocess.Popen(['git', 'checkout','master','--','actionsStatus.py'], stdout=subprocess.PIPE, cwd=script_dir)
        stdout = process.communicate()[0]
        stdout = stdout.decode('utf-8')
        up_to_date = ("Already up to date" in stdout)
        if not up_to_date:
            print("actionsStatusCLI has been updated automatically after running")

    def update_local(self):
        """
        updates the local list of workflows on the repo
        :return:
        """
        response = requests.get(
            'https://api.github.com/repos/{owner}/{repo}/actions/workflows'.format(owner=self.repo_owner,
                                                                                   repo=self.repo),
            auth=(self.access_token, 'x-oauth-basic'))
        if response.status_code != 200:
            print("Failed to get workflows for repo {}".format(self.repo))
            print("Perhaps token is invalid or has insufficient permissions")
            self.timeout_reached = True
            self.has_running_actions = False
            self.exiting = True
            return

        repo_workflows = json.loads(response.text)
        for workflow in repo_workflows["workflows"]:
            # run count set to 0 on get since it is got only when checking for runs
            self.workflows.append({"name": workflow["name"], "id": workflow["id"], "run_count": 0})

    def get_user_and_repo_from_cwd(self):
        """
        Gets the repo info (owner + name) from the directory it was called in
        :return:
        """
        with open(".git/config", "r") as git_config:
            cfg_lines = git_config.readlines()
            for line in cfg_lines:
                if "url = " in line:
                    if "git@" in line:
                        self.repo_owner = line[line.find(":") + 1:line.find("/")]
                        self.repo = line[line.find("/") + 1:line.find(".git")]
                    elif "https:" in line:
                        self.repo_owner = line[line.find("github.com/") + 11:line.rfind("/")]
                        self.repo = line[line.rfind("/") + 1:line.find(".git")]




    def load_access_token(self):  # TODO
        """
        Loads access token from file
        :return:
        """
        script_dir = os.path.dirname(__file__)
        token_path = os.path.join(script_dir, "token.txt")
        with open(token_path, "r") as token_file:
            token = token_file.read().strip()
            self.access_token = token

    def get_running_actions(self):
        """
        pings a repo for running actions and sets the self.running_actions to the list of runnning actions
        :return: set of running action ids
        """
        list_of_running_workflow_ids = set()

        # for all actions that repo has, check for running ones
        for workflow in self.workflows:
            if self.exiting:
                break
            id = workflow["id"]
            response = requests.get(
                'https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs'.format(
                    owner=self.repo_owner, repo=self.repo, workflow_id=id), auth=(self.access_token, 'x-oauth-basic'))
            workflow_runs_on_repo = json.loads(response.text)
            workflow["run_count"] = workflow_runs_on_repo["total_count"]
            runs = workflow_runs_on_repo["workflow_runs"]

            for run in runs:
                if run["status"] != "completed":
                    list_of_running_workflow_ids.add(run["id"])

        return list_of_running_workflow_ids

    def run(self):
        """
        The main section of the program
        :return:
        """
        # if token failed, then exit
        if self.exiting:
            return

        # starts countdown timeout in background
        timer_thread = threading.Timer(len(self.workflows) * self.timeout_to_find_running_actions, self.timer_done)
        timer_thread.start()

        # start a thread to update the running actions set
        running_actions_thread = threading.Thread(target=self.update_running_actions_id_set_thread)
        running_actions_thread.start()

        # makes output based on each running action into a table
        # if table changes, update it in place
        last_lines = []
        while True:
            try:
                lines = self.make_output_text_lines()
                if last_lines != lines:
                    self.print_output(lines)
                time.sleep(.5)
                last_lines = lines
                if self.timeout_reached and not self.has_running_actions:
                    break
            except KeyboardInterrupt:
                # allow easy exit
                print("CTRL-C recieved; exiting")
                self.exiting = True
                self.has_running_actions = False
                break

        # print failed outputs
        if len(self.dict_of_failed_actions.keys()) > 0:
            print("Failed runs logs can be found at")
            table_list = []
            for key in self.dict_of_failed_actions.keys():
                line_row = [key, self.dict_of_failed_actions[key]]
                table_list.append(line_row)
            logs_output = self.print_as_table(table_list)
            print(logs_output)
        # print if no actions found
        if len(self.set_of_running_action_ids) == 0:
            print("\nNo running actions found for {}".format(self.repo))

        running_actions_thread.join()
        timer_thread.join()

        return

    def print_output(self, lines):
        """
        outputs the table of actions/status to the console
        :param lines: input list of lines to turn into a table
        """
        if len(self.set_of_running_action_ids) > 0:
            table_list = []
            for name, status, result in zip(*[iter(lines)] * 3):
                line_row = name, status, result  # , aux
                table_list.append(line_row)
            output = self.print_as_table(table_list)
            self.overwrite_console(output)
            # print(output)
        else:
            # print("ssss")
            self.overwrite_console("Finding running actions...")

    def overwrite_console(self, multiline_output):
        """
        Overwrites the console with multiple lines
        if more lines are needed/ output grew, will also expand
        :param multiline_output:
        :return:
        """
        magic_char = '\033[F'
        num_lines = multiline_output.count('\n')
        # if there has not been a table writen or table grew, give more lentgth to write
        if num_lines > self.len_of_overwrite_output:
            for i in range(0, num_lines - self.len_of_overwrite_output):
                print("")
            self.len_of_overwrite_output = num_lines
        ret_depth = magic_char * self.len_of_overwrite_output

        print('{}{}'.format(ret_depth, multiline_output), end='', flush=True)

    def print_as_table(self, tbl, borderHorizontal='-', borderVertical='|', borderCross='+'):
        """
        Makes a table from lists
        :param tbl: list of lists where each sublist is a table row and item = column
        :param borderHorizontal:
        :param borderVertical:
        :param borderCross:
        :return: multiline string that is the table
        """
        cols = [list(x) for x in zip(*tbl)]
        lengths = [max(map(len, map(str, col))) for col in cols]
        f = borderVertical + borderVertical.join(' {:>%d} ' % l for l in lengths) + borderVertical
        s = borderCross + borderCross.join(borderHorizontal * (l + 2) for l in lengths) + borderCross

        table_str = ""
        table_str += s + "\n"
        for row in tbl:
            table_str += f.format(*row) + "\n"
            table_str += s + "\n"

        return table_str

    def make_output_text_lines(self):
        """
        Takes current status of all actions and returns lines to be rows of output table
        :return: list of lines to be made into a table
        """
        action_text_lines = ["Workflow", "Status", "Result"]
        for action_run in self.set_of_running_action_ids:
            if action_run not in self.set_of_completed_action_ids:
                line_name, line_status, line_result, line_aux = self.get_workflow_run(action_run)
                action_text_lines.append(line_name)
                action_text_lines.append(line_status)
                action_text_lines.append(line_result)
                # action_text_lines.append(line_aux)

                # TODO add this to work
                # if line_status == "completed":
                #    self.set_of_completed_action_ids.add(action_run)

        return action_text_lines

    def get_workflow_run(self, run_id):
        """
        gets details on a github action run
            status
            workflow name
            result
        :param run_id: id of github action run
        :return:
        """
        response = requests.get(
            'https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}'.format(owner=self.repo_owner,
                                                                                       repo=self.repo, run_id=run_id),
            auth=(self.access_token, 'x-oauth-basic'))
        workflow_run = json.loads(response.text)
        status = workflow_run["status"]

        conclusion = workflow_run["conclusion"]

        for workflow in self.workflows:
            if workflow["id"] == workflow_run["workflow_id"]:
                workflow_name = workflow["name"]
                break

        # output logs if not done or if failed
        if conclusion and conclusion != "success":
            aux_output = "https://github.com/{repo_owner}/{repo}/actions/runs/{run_id}".format(
                repo_owner=self.repo_owner, repo=self.repo, run_id=run_id)
            self.dict_of_failed_actions[workflow_name] = aux_output
        else:
            aux_output = ""

        if not conclusion:
            conclusion = ""

        return workflow_name, status, conclusion, aux_output

    def timer_done(self):
        """
        Starts after timer via threading
        sets timeout reached to True
        :return:
        """
        self.timeout_reached = True

    def update_running_actions_id_set_thread(self):
        """
        Updates the set of running action ids
        """
        while True:

            current_actions = self.get_running_actions()
            # only adds to set
            if len(current_actions) > len(self.set_of_running_action_ids):
                self.set_of_running_action_ids = self.get_running_actions()

            if len(current_actions) > 0:
                self.has_running_actions = True
            else:
                self.has_running_actions = False

            # break if timeout is reached and nothing is running
            if self.timeout_reached and not self.has_running_actions:
                break
        return


if __name__ == "__main__":
    # make new class
    actionsStatus = actionsStatus()
    # tell it to update its vars and get all actions/workflows
    actionsStatus.update_local()
    # run main program
    actionsStatus.run()
    actionsStatus.check_for_update()

    # TODO check for update from its repo
