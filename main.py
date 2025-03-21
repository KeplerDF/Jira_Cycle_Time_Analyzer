import os
import calendar
import pandas as pd
from jira import JIRA
import datetime
from datetime import datetime
import matplotlib.pyplot as plt
import dateutil.relativedelta
import PySimpleGUI as sg
from jira.exceptions import JIRAError
import tkinter as tk


# Create an authentication object,using
# registered emailID, and, token received.

name = "user"
user_token = "token"
user_server = "server"
epic = "epic"


def config_user(search_type):
    df = pd.read_json("user_config.json")
    if not df.at[search_type, 'config']:
        window = sg.Window("There is no" + search_type + " config")
        window.close()
    return df.at[search_type, 'config']


user = config_user(name) + ENVVAREMAILADDRESS
token = ENVVARUSERTOKEN


def jira_analyser():
    # Ignoring error caused on macOS due to NSApplicationDelegate.applicationSupportsSecureRestorableState: Error
    f = open("/dev/null", "w")
    os.dup2(f.fileno(), 2)
    f.close()
    # Running programs initial buttons
    button_layout()


def set_user_as_target():
    jql_command = "assignee = " + config_user(name)
    error_handling(jql_command)


def set_epic_as_target():
    jql_command = "cf[10006] = " + config_user(epic)
    error_handling(jql_command)


def error_handling(jql_command):
    try:
        jira_kickoff(jql_command)
    except KeyboardInterrupt:
        print()
        print("Error: You have Interrupted the Program")
    except JIRAError as e:
        print("Status:" + str(e.status_code))
        print(e.response)
        print("Error:" + e.text)
        print("Error: Jira API is not happy")


def jira_kickoff(jql_command):
    jira = return_jira()
    list_jiras_for_month(jira, jql_command)


def return_jira():
    options = {
        'server': config_user(user_server)
    }
    jira = JIRA(options=options, token_auth=token)
    return jira


def terminal_headers():
    print('{}'.format("".ljust(150, "-")))
    print('{} | {} | {}'.format("Jira ".ljust(20), "Summary".ljust(50), "In Progress (Days)"))
    print('{}'.format("".ljust(150, "-")))


def button_layout():
    parent = tk.Tk()
    frame = tk.Frame(parent)
    frame.pack()
    text_disp = tk.Button(frame, text="Individual Jira Cycles", command=set_user_as_target, activeforeground="blue")
    text_disp.pack(side=tk.LEFT)
    text_disp_epic = tk.Button(frame, text="Jira Cycle times for epic", command=set_epic_as_target, activeforeground="blue")
    text_disp_epic.pack(side=tk.RIGHT)
    parent.mainloop()


def list_jiras_for_month(jira, jql):
    terminal_headers()
    '''''''''
    
    check_for_assignee = False
    if "assignee" in jql:
        check_for_assignee = True
        
    '''''''''
    list_of_jiras = list_jiras_per_month(jira, jql)
    total = len(list_of_jiras) - 1
    x = 0
    dict_of_averages = {}
    while x <= total:
        average_jira = []
        for n in list_of_jiras[x]:
            ticket = n.key
            issue = jira.issue(ticket)

            change_logs = jira.issue(id=ticket, expand='changelog')

            # Json pointer for where we have to look for the "selected for development date:"
            # /changelog/histories/6/items/0/field print(change_logs)

            if issue.fields.resolutiondate:
                done_date = issue.fields.resolutiondate

                development_date = cycle_get_development_start(change_logs, "status", "Selected for Development")
                progress_date = cycle_get_development_start(change_logs, "status", "In Progress")

                '''''''''
                
                # if the JQL contains "assignee" 
                # then the date at which the user was assigned to the jira will be the first date to be added to the list of dates
                if check_for_assignee:
                    assignee_date = cycle_get_development_start(change_logs, "assignee", separate_user_name(config_user(name)))
                    list_of_dates = consolidate_dates(list_of_dates, assignee_date)
                    
                '''''''''
                dict_of_dates = {}
                if check_null(development_date):
                    dict_of_dates = {"Selected for Development": development_date}
                if check_null(progress_date):
                    dict_of_dates = {"In Progress": progress_date}

                if dict_of_dates:
                    items = [i for a, i in enumerate(dict_of_dates.items()) if i is not None]
                    dates = items[0]
                    start_date = dates[1]
                    cycle = format_cycle_time(start_date, done_date)
                    average_jira.append(cycle)
                    print(
                        '{} | {} | {}: {}'.format(issue.key.ljust(20)[:20], issue.fields.summary.ljust(50)[:50], dates[0], str(cycle)))

        # list_of_averages.append(get_average(average_jira))
        # list_of_months.append(calendar.month_name[datetime.today().month - x])
        dict_of_averages[calendar.month_name[datetime.today().month - x]] = get_average(average_jira)
        print("")
        print("Your average jira cycle time over the month of " + calendar.month_name[
            datetime.today().month - x] + " is " + str(round(get_average(average_jira), 2)) + " days")
        print("")
        x = x + 1
    draw_diagram(dict_of_averages)


def check_null(date):
    if date != "No Date":
        return date


def separate_user_name(username):
    result = username.split(".")
    for n in range(len(result)):
        result[n] = result[n].capitalize()
    name_to_return = result[0] + " " + result[1]
    return name_to_return


def draw_diagram(dict_of_averages):
    # Create a DataFrame from the dict of data
    keys = dict_of_averages.keys()
    values = dict_of_averages.values()
    df = pd.DataFrame(values, columns=['Values'])
    df.index = keys
    df = df.iloc[::-1]
    # df.index = reversed_months
    df['Values'].plot()

    plt.title('Diagram of cycle times in days for every month')
    plt.show()


# This method gets the date of a month ago in the format yyyy-MM-dd
def list_jiras_per_month(jira, jql):
    datetime.today().replace(day=1)
    date_now = datetime.now().today().replace(day=1)
    number_of_months = 12
    list_of_results = []
    n = 0
    while n < number_of_months:
        last_month = date_now - dateutil.relativedelta.relativedelta(months=n)
        list_of_results.append(get_every_month(jira, last_month, jql))
        n = n + 1

    return list_of_results


def get_every_month(jira, month, jql):
    month_plus_one = month + dateutil.relativedelta.relativedelta(months=1)
    jql_string = (
            jql + " AND resolved >= " + str(month.strftime('%Y-%m-%d')) + " AND resolved < " + str(month_plus_one.strftime('%Y-%m-%d')) + " ORDER BY key DESC")

    return jira.search_issues(jql_str=jql_string, maxResults=10, fields='key')


# This method uses start and end date of a card to return a cycle time in days
def format_cycle_time(start, end):
    start_date = datetime.strptime(str(start), "%Y-%m-%dT%H:%M:%S.%f%z")
    end_date = datetime.strptime(str(end), "%Y-%m-%dT%H:%M:%S.%f%z")
    return abs((end_date - start_date).days)


# this method takes in an issue jira, finds the history object that corresponds to when the jira was "Selected for
# Development" and returns the date of that status change
def cycle_get_development_start(issue, item_type, status_string):
    for n in issue.changelog.histories:
        number_of_items = len(n.items)
        x = 0
        while x < number_of_items:
            selected_for_development = n.items[x].toString
            field = n.items[x].field

            if field == item_type and selected_for_development == status_string:
                dev_start_time = n.created

                return dev_start_time
            x = x + 1

    return "No Date"


# 'Current Status', 'Status'
# (Status = To Do OR Status = In Progress) OR (status = "Done" AND Status Changed to "Done" AFTER "-1m")
def get_average(list_of_days):
    length_of_list = len(list_of_days)
    if length_of_list == 0:
        return 0
    total = 0
    for n in list_of_days:
        total = total + n
    return total / length_of_list


if __name__ == '__main__':
    jira_analyser()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
