import os
from time import time
import requests
from requests_oauthlib import OAuth1
from argparse import ArgumentParser
from configparser import ConfigParser


ACCOUNT = "yourUserAccount"

def xmit(url, payload, action, creds):
    headers = {'user-agent': "Steward-Magik by Operator873 operator873@gmail.com"}

    if action == "post":
        r = requests.post(url, headers=headers, data=payload["payload"], auth=creds)
    elif action == "authget":
        r = requests.get(url, headers=headers, params=payload["payload"], auth=creds)
    else:
        r = requests.get(url, headers=headers, params=payload["payload"])

    return r.json()


def get_creds():
    config = ConfigParser()
    config.read(f"{os.path.dirnam(__file__)}/magik.conf")

    creds = []
    for _k, value in config.items("consumer"):
        creds.append(value)

    return tuple(creds)
    

def get_api_url(proj):
    try:
        lang, site = proj.replace("wik", "+wik").split("+")
    except ValueError:
        if proj == "commons":
            lang, site = ("commons", "wikimedia")
        elif proj == "meta":
            lang, site = ("meta", "wikimedia")
        else:
            print(f"Error processing {proj}. Try things like 'enwiki' or 'meta'.")
            SystemExit

    if site == "wiki":
        if lang == "meta":
            site = "wikimedia"
        else:
            site = "wikipedia"
    
    if site == "wikt":
        site = "wiktionary"
    
    return f"https://{lang}.{site}.org/w/api.php"


def do_block(creds, cmd):
    apiurl = get_api_url(cmd.project)
    target = "_".join(cmd.target)

    token = get_token(creds, 'csrf')

    if cmd.action == "unblock":
        block_request = {
        "action": "unblock",
        "user": cmd.target,
        "reason": cmd.reason,
        "token": token,
        "format": "json",
        }
    
    else:
        block_request = {
            "action": "block",
            "user": target,
            "expiry": cmd.duration,
            "reason": cmd.reason,
            "token": token,
            "allowusertalk": "",
            "nocreate": "",
            "autoblock": "",
            "format": "json",
        }

        if (
            cmd.action == "reblock"
            or cmd.force
        ):
            block_request["reblock"] = ""

        if cmd.softblock:
            del block_request["autoblock"]
        
        if cmd.revoketpa:
            del block_request["allowusertalk"]
        
        if cmd.allowcreate:
            del block_request["nocreate"]
    
    process_response(xmit(apiurl, block_request, "post", creds))


def do_lock(creds, cmd):
    site = "https://meta.wikimedia.org/w/api.php"

    token = get_token(creds, 'setglobalaccountstatus')

    lock = {
        "action": "setglobalaccountstatus",
        "format": "json",
        "user": cmd.target,
        "locked": cmd.action,
        "reason": cmd.reason,
        "token": token,
    }

    data = xmit(site, lock, "post", creds)

    if "error" in lock:
        print(f"""FAILED! {data["error"]["info"]}""")
    else:
        print(f"{cmd.target} {cmd.action}ed.")


def do_gblock(creds, cmd):
    site = "https://meta.wikimedia.org/w/api.php"
    token = get_token(creds, 'csrf')

    block = {
        "action": "globalblock",
        "format": "json",
        "target": cmd.target,
        "expiry": cmd.duration,
        "reason": cmd.reason,
        "alsolocal": True,
        "token": token,
    }

    if cmd.anononly:
        block["anononly"] = True
        block["localanononly"] = True
    
    if cmd.force:
        block["modify"] = True
    
    gblock = xmit(site, block, "post", creds)

    if "error" in gblock:
        failure = gblock["error"]["globalblock"][0]
        if failure["code"] == "globalblocking-block-alreadyblocked":
            response = "The target is already blocked."
        else:
            response = "Block failed! " + str(failure["message"])
    elif "block" in gblock or "globalblock" in gblock:
        expiry = gblock["globalblock"]["expiry"]
        if cmd.force:
            response = "Block was modified. New expiry: " + expiry
        elif "anononly" in block:
            response = "Anon-only block succeeded. Expiry: " + expiry
        else:
            response = "Block succeeded. Expiry: " + expiry
    else:
        response = "Unknown failure... " + gblock
    
    print(response)

def do_test(creds, cmd):
    pass


def do_mass(creds, cmd):
    pass


def get_token(creds, token_type, url):
    reqtoken = {"action": "query", "meta": "tokens", "format": "json", "type": token_type}
    
    token = xmit(url, reqtoken, "authget", creds)

    if "error" in token:
        print(token["error"]["info"])
        SystemExit
    else:
        return token["query"]["tokens"]["%stoken" % token_type]


def process_response(data, cmd):
    if "block" in data:
        print(f"""{data["block"]["user"]} was blocked until {data["block"]["expiry"]} with reason: {data["block"]["reason"]}""")
    
    if "unblock" in data:
        user = data["unblock"]["user"]
        reason = data["unblock"]["reason"]
        print(f"{user} was unblocked with reason: {reason}")

    if "globalblock" in data:
        expiry = data["globalblock"]["expiry"]
        if cmd.force:
            print(f"Global block was modified! New expiry: {expiry}")
        elif cmd.anononly:
            print(f"Anon-only global block succeeded. Expiry: {expiry}")
        else:
            print(F"Block succeeded. Expiry: {expiry}")

    if "error" in data:
        if "globalblock" in data["error"]:
            failure = data["error"]["globalblock"][0]
            if failure["code"] == "globalblocking-block-alreadyblocked":
                print("The target is already blocked.")
            else:
                print(f"""Block failed! {failure["message"]}""")
        
        else:
            reason = data["error"]["code"]
            if reason == "badtoken":
                response = "Received CSRF token error. Try again..."
            elif reason == "alreadyblocked":
                response = (
                    data["target"]
                    + " is already blocked. Use reblock or --force to change the current block."
                )
            elif reason == "permissiondenied":
                response = (
                    "Received permission denied error. Are you a sysop on "
                    + data["project"]
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



def main(cmd):
    # Check to see if configuration exists
    if not os.path.exists(f"{os.getcwd()}/magik.conf"):
        print("The magik.conf file is missing and should have been pulled with the package. Please do 'git pull' again.")
        SystemExit
    
    # Make sure the config file has been updated
    creds = get_creds()
    if (
        "a" in creds
        or "b" in creds
        or "c" in creds
        or "d" in creds
    ):
        print("It seems like maybe you haven't configured your consumer information. See https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration")
        SystemExit

    if (
        cmd.action == "block"
        or cmd.action == "unblock"
        or cmd.action == "reblock"
    ):
        do_block(creds, cmd)
    
    elif (
        cmd.action == "lock"
        or cmd.action == "unlock"
    ):
        do_lock(creds, cmd)
    
    elif (
        cmd.action == "gblock"
        or cmd.action == "ungblock"
        or cmd.action == "regblock"
    ):
        do_gblock(creds, cmd)
    
    elif cmd.action == "test":
        do_test(creds, cmd)
    
    elif cmd.action == "mass":
        if cmd.file:
            do_mass(creds, cmd)
        else:
            print("Use the --file switch to pass a path to the file containing the targets, one per line.")
    
    else:
        print(f"I don't know how to '{cmd.action}'")


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "action",
        help="What action to perform [(un)block, (un)lock, (un)gblock]",
        required=True,
    )

    parser.add_argument(
        "-t",
        "--target",
        nargs="+",
        help="The target of the operation",
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

    args = parser.parse_args()

    main(args)