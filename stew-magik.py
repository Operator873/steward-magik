#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from configparser import ConfigParser

import requests
from requests_oauthlib import OAuth1


# This is a requests wrapper to make life easier
def xmit(url, payload, action):
    # Headers let the server owners know who's responsible for the misery the API endures
    # Provide contact info and such
    headers = {"user-agent": "Steward-Magik by Operator873 operator873@gmail.com"}
    creds = get_creds()

    if action == "post":
        r = requests.post(url, headers=headers, data=payload, auth=creds)
    elif action == "authget":
        r = requests.get(url, headers=headers, params=payload, auth=creds)
    else:
        r = requests.get(url, headers=headers, params=payload)

    if r.ok:
        return r.json()
    else:
        print(r)
        raise SystemExit()


# Check the file is renamed and contains the appropriate information
def get_creds():
    config = ConfigParser()
    config.read(f"""{os.path.expanduser("~")}/.magik""")

    # Glob up consumer tokens, disregard the key and add the values
    creds = []
    for _k, value in config.items("consumer"):
        creds.append(value)

    not_set = ["a", "b", "c", "d"]

    # Check each of the stored creds against what the repo ships with to see if the user didn't follow directions
    # Because users do that
    # A lot
    if any(i in not_set for i in creds):
        print(
            "It seems like maybe you haven't configured your consumer information. See https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration"
        )
        raise SystemExit()

    result = OAuth1(creds[0], creds[1], creds[2], creds[3])

    return result


# A devilishly smart way of figuring out which API to use
def get_api_url(proj):
    # Look for "wik" to split on
    try:
        lang, site = proj.replace("wik", "+wik").split("+")
    except ValueError:
        if proj == "commons":
            lang, site = ("commons", "wikimedia")
        elif proj == "meta":
            lang, site = ("meta", "wikimedia")
        else:
            print(f"Error processing {proj}. Try things like 'enwiki' or 'meta'.")
            raise SystemExit()

    # Why does meta have to be so different?
    if site == "wiki":
        if lang == "meta":
            site = "wikimedia"
        else:
            site = "wikipedia"

    # Wiktionary
    if site == "wikt":
        site = "wiktionary"

    return f"https://{lang}.{site}.org/w/api.php"


# with the information in hand, process a block
def do_block(target, cmd):
    try:
        target = "_".join(target)
        reason = process_reason(" ".join(cmd.reason))
        duration = "".join(cmd.duration) if cmd.action == "block" else ""
        project = cmd.project
    except TypeError:
        print(
            f"Blocks require target, reason, project, and duration. Supplied was:\n{cmd}"
        )
        return

    # cleverly split up shorthand project into an API address
    apiurl = get_api_url(project)
    token = get_token("csrf", apiurl)

    if cmd.action == "unblock":
        block_request = {
            "action": "unblock",
            "user": target,
            "reason": reason,
            "token": token,
            "format": "json",
        }

    else:
        block_request = {
            "action": "block",
            "user": target,
            "expiry": duration,
            "reason": reason,
            "token": token,
            "allowusertalk": "",
            "nocreate": "",
            "autoblock": "",
            "format": "json",
        }

        if cmd.action == "reblock" or cmd.force:
            block_request["reblock"] = ""

        if cmd.softblock:
            del block_request["autoblock"]

        if cmd.revoketpa:
            del block_request["allowusertalk"]

        if cmd.allowcreate:
            del block_request["nocreate"]

    # If this is a dryrun, don't actually do it
    if cmd.test:
        print(apiurl)
        print(block_request)
    else:
        process_response(xmit(apiurl, block_request, "post"), cmd)


# Process a lock with the supplied information
def do_lock(user, cmd):
    # Site up some variables first
    site = "https://meta.wikimedia.org/w/api.php"
    token = get_token("setglobalaccountstatus", site)
    try:
        target = "_".join(user)
        reason = process_reason(" ".join(cmd.reason))
    except TypeError:
        print(f"Locks require target and reason. Supplied was: {cmd}")
        return

    # Lock payload is straight forward
    lock = {
        "action": "setglobalaccountstatus",
        "format": "json",
        "user": target,
        "locked": cmd.action,
        "reason": reason,
        "token": token,
    }

    if cmd.action == "lock":
        if hasattr(cmd, "hide"):
            lock['hidden'] = "lists"
        
        if hasattr(cmd, "suppress"):
            lock['hidden'] = "suppressed"

    # If this is a dryrun, don't actually do it
    if cmd.test:
        print(site)
        print(lock)
    else:
        data = xmit(site, lock, "post")

        # Handle error or success
        if "error" in data:
            print(f"""FAILED! {data["error"]["info"]}""")
        else:
            print(f"""{target} {cmd.action}ed.""")


# Do a global block with the supplied information
def do_gblock(target, cmd):
    # Do some setup work
    site = "https://meta.wikimedia.org/w/api.php"
    token = get_token("csrf", site)
    try:
        target = "_".join(target)
        reason = process_reason(" ".join(cmd.reason))
        duration = "".join(cmd.duration) if cmd.action == "gblock" else ""
    except TypeError:
        print(
            f"Global blocks require target, reason, and duration. Supplied was: {cmd}"
        )
        return

    if cmd.action == "ungblock":
        # The payload is different depending on the action
        block = {
            "action": "globalblock",
            "format": "json",
            "target": target,
            "token": token,
            "reason": reason,
            "unblock": "",
        }

    else:
        block = {
            "action": "globalblock",
            "format": "json",
            "target": target,
            "expiry": duration,
            "reason": reason,
            "alsolocal": True,
            "token": token,
        }

    # Check for and handle anononly
    if cmd.anononly:
        block["anononly"] = True
        block["localanononly"] = True

    # Check for and handle force or reblock
    if cmd.force:
        block["modify"] = True

    # If this is a dryrun, don't actually do it
    if cmd.test:
        print(site)
        print(block)
    else:
        process_response(xmit(site, block, "post"), cmd)


# Tokens are needed as part of authentication process. Handle them all here
def get_token(token_type, url):
    reqtoken = {
        "action": "query",
        "meta": "tokens",
        "format": "json",
        "type": token_type,
    }

    token = xmit(url, reqtoken, "authget")

    if "error" in token:
        print(token["error"]["info"])
        raise SystemExit()
    else:
        return token["query"]["tokens"]["%stoken" % token_type]


# Clean up the API response from mediawiki and parse the output for human readability
def process_response(data, cmd):
    if "block" in data:
        # A succesful block occurred
        print(
            f"""{data["block"]["user"]} was blocked until {data["block"]["expiry"]} with reason: {data["block"]["reason"]}"""
        )

    if "unblock" in data:
        # A successful unblock
        user = data["unblock"]["user"]
        reason = process_reason(data["unblock"]["reason"])
        print(f"{user} was unblocked with reason: {reason}")

    if "globalblock" in data:
        # Successful gblock
        # {'globalblock': {'blockedlocally': '', 'user': 'ip.add.re.ss', 'blocked': '', 'expiry': '2023-07-04T08:04:36Z'}}
        # Successful ungblock
        # {'globalblock': {'user': 'ip.add.re.ss', 'unblocked': ''}}
        if "expiry" in data["globalblock"]:
            expiry = data["globalblock"]["expiry"]
            if cmd.force:
                print(f"Global block was modified! New expiry: {expiry}")
            elif cmd.anononly:
                print(f"Anon-only global block succeeded. Expiry: {expiry}")
            else:
                print(f"Global block succeeded. Expiry: {expiry}")
        else:
            if "unblocked" in data["globalblock"]:
                print(f"{data['globalblock']['user']} was globally unblocked.")

    if "error" in data:
        # An error occurred during the API interactions
        if "globalblock" in data["error"]:
            # Global block erros don't really have much info to parse
            failure = data["error"]["globalblock"][0]
            if failure["code"] == "globalblocking-block-alreadyblocked":
                print("The target is already blocked.")
            else:
                print(f"""Block failed! {failure["message"]}""")

        else:
            # ALl others have rich information to parse
            reason = data["error"]["code"]
            if reason == "badtoken":
                response = "Received CSRF token error. Try again..."
            elif reason == "alreadyblocked":
                print()
                response = (
                    data["error"]["info"]
                    + " Use reblock or --force to change the current block."
                )
            elif reason == "permissiondenied":
                response = (
                    "Received permission denied error. Are you a sysop on "
                    + data["error"]["project"]
                    + "?"
                )
            elif reason == "invalidexpiry":
                response = (
                    "The expiration time isn't valid. "
                    + "I understand things like 31hours, 1week, 6months, infinite, indefinite."
                )
            else:
                info = data["error"]["info"]
                code = data["error"]["code"]
                response = "Unhandled error: " + code + " " + info

            print(response)


# Create some short cuts that can be passed with --reason
def process_reason(reason):
    if reason == "proxy":
        return "[[m:Special:MyLanguage/NOP|Open proxy]]: See the [[m:WM:OP/H|help page]] if you are affected"
    elif reason.startswith("webhost"):
        try:
            _c, msg = reason.split(" ", 1)
        except ValueError:
            msg = ""
        return f"[[m:Special:MyLanguage/NOP|Open proxy/Webhost]]: See the [[m:WM:OP/H|help page]] if you are affected: {msg}"
    elif reason == "lta":
        return "Long term abuse"
    elif reason == "spambot":
        return "Cross-wiki spam: spambot"
    elif reason == "spam":
        return "Cross-wiki spam"
    else:
        return reason


# Decide what to do based on what switches were applied
def main(cmd):
    # Check to see if configuration exists
    if not os.path.exists(os.path.expanduser("~/.magik")):
        print(
            "You are not currently configured. Check the 'magik.conf' file for instructions."
        )
        return
    

    # If we are doing local project specific blocks, use do_block
    if cmd.action == "block" or cmd.action == "unblock" or cmd.action == "reblock":
        # Handle a personal habit of mine
        if cmd.action != "unblock":
            if "forever" in cmd.duration:
                cmd.duration = ["indefinite"]

        for t in cmd.target:
            do_block(t, cmd)

    # If we are doing Steward Locks, do_lock
    elif cmd.action == "lock" or cmd.action == "unlock":
        for t in cmd.target:
            do_lock(t, cmd)

    # If we are doing Steward Global Blocks, do_gblock
    elif cmd.action == "gblock" or cmd.action == "ungblock" or cmd.action == "regblock":
        # Handle a personal habit of mine
        if cmd.action != "ungblock":
            if "forever" in cmd.duration:
                cmd.duration = ["indefinite"]

        for t in cmd.target:
            do_gblock(t, cmd)

    # Handle a dryrun or test switch by just coughing out the cmd
    elif cmd.action == "test":
        list_of_nicks = cmd.target.split(",")
        for nick in list_of_nicks:
            print(f"{nick}: {cmd.reason}")

    # Users will be users
    else:
        print(f"I don't know how to '{cmd.action}'")


# Make sure this is not being called by something else
if __name__ == "__main__":
    # Build the arg parser
    parser = ArgumentParser()

    parser.add_argument(
        "action",
        help="What action to perform [(un)block, (un)lock, (un)gblock]",
        choices=[
            "block",
            "unblock",
            "reblock",
            "gblock",
            "ungblock",
            "regblock",
            "lock",
            "unlock",
            "test",
        ],
    )

    parser.add_argument(
        "-t",
        "--target",
        action="append",
        nargs="+",
        help="The target of the operation. Can be used multiple times in the same command (multiple targets, same block).",
    )

    parser.add_argument(
        "-p",
        "--project",
        help="Which project to do the action on",
    )

    parser.add_argument(
        "-d",
        "--duration",
        "--until",
        nargs="+",
        help="How long a block is for",
    )

    parser.add_argument(
        "-r",
        "--reason",
        nargs="+",
        help="Add a reason to the action",
    )

    parser.add_argument(
        "--revoketpa",
        "--tpa",
        help="Revoke Talk Page Access",
        const=True,
        nargs="?",
        metavar="",
    )

    parser.add_argument(
        "--allowcreate",
        help="Allow account creation",
        const=True,
        nargs="?",
        metavar="",
    )

    parser.add_argument(
        "--softblock",
        "--noautoblock",
        help="Disable the auto-block of any other accounts from the IP. (softblock)",
        const=True,
        nargs="?",
        metavar="",
    )

    parser.add_argument(
        "-f",
        "--force",
        "--reblock",
        const=True,
        nargs="?",
        help="Force the block over an existing block.",
    )

    parser.add_argument(
        "--anononly",
        "--anon",
        help="Enable anonymous only block",
        const=True,
        nargs="?",
        metavar="",
    )

    parser.add_argument(
        "--test",
        "--dryrun",
        help="Don't actually send anything, just show the query that would be sent.",
        const=True,
        nargs="?",
    )

    parser.add_argument(
        "--hide",
        "--hidden",
        help="Hide the locked account from global user lists.",
        const=True,
        nargs="?",
    )

    parser.add_argument(
        "--suppress",
        "--suppressed",
        help="Suppress the locked account name.",
        const=True,
        nargs="?",
    )

    args = parser.parse_args()

    # Lets get started
    main(args)
