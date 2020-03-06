#!/usr/bin/env python3
"""Generic cloudwatch stack installer

TODO:
    finish this so it builds the correct CF stack
    for cloudwatch cross-account role
    see: all tabs in cf-cross
"""
import sys
import time
import ccalogging
from getopt2 import getopt2
from typing import List
from typing import Tuple
import boto3
from botocore.exceptions import ClientError
from chaim.chaimmodule import Chaim
from cfntool.errors import errorExit
from cfntool.errors import errorRaise
from cfntool.cfnclient import CFNClient
from cfntool import __version__

ccalogging.setConsoleOut()
ccalogging.setInfo()
log = ccalogging.log

USAGE = """
install-template.py [-options]

options:
    -h This help
    -m parameter list string:
          'something=somevalue,somethingelse=someothervalue'
    -P profile to use to install the stack (not required if 'all' is chosen)

required options:
    -a account name
    -n name of stack
    -p product tag
    -t full path to Cloudformation template to use

All actions are mutually exclusive
you must provide one action

Actions:
    -A install/update all accounts
    -D delete named stack
    -I install/update the named stack
    -S status of named stack

if you provide more than one action, the last one on the
command line 'wins'.
"""


def usage():
    sys.exit(USAGE)


def makeParamDict(strparams):
    try:
        pd = {}
        if "=" in strparams:
            ea = strparams.split(",")
            for p in ea:
                tmp = p.split("=")
                pd[tmp[0].strip()] = tmp[1].strip()
        return pd
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorRaise(fname, e)


def expandDictToList(xdict, keyname="Key", valuename="Value"):
    try:
        op = []
        for key in xdict:
            tmp = {keyname: key, valuename: xdict[key]}
            op.append(tmp)
        return op
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorRaise(fname, e)


def buildStackTags(options):
    try:
        gtags = {
            "owner": "sre",
            "environment": "prod",
            "product": options["product"],
            "role": "stack",
            "version": __version__,
        }
        return expandDictToList(gtags)
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorRaise(fname, e)


def buildStackParams(options):
    try:
        pd = makeParamDict(options["params"])
        lpd = expandDictToList(pd, keyname="ParameterKey", valuename="ParameterValue")
        return lpd
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorRaise(fname, e)


def getTemplate(fn):
    try:
        op = None
        with open(fn, "r") as ifn:
            lines = ifn.readlines()
        for line in lines:
            if op is None:
                op = line
            else:
                op += line
        return op
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorRaise(fname, e)


def buildStackDict(options):
    try:
        template = getTemplate(options["templatefn"])
        if template is None:
            raise Exception(f"""Failed to read {options["templatefn"]}""")
        xd = {"StackName": options["stackname"], "TemplateBody": template}
        xd["Parameters"] = buildStackParams(options)
        xd["Capabilities"] = ["CAPABILITY_NAMED_IAM"]
        xd["Tags"] = buildStackTags(options)
        return xd
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorRaise(fname, e)


def checkStack(stack):
    ok = False
    log.debug(f"checking stack: {stack}")
    if "StackStatus" in stack:
        log.debug("status is in stack")
        if stack["StackStatus"] in ["UPDATE_COMPLETE", "CREATE_COMPLETE"]:
            log.debug("is one of the updates")
            if "Tags" in stack:
                log.debug("stack has tags")
                for tag in stack["Tags"]:
                    if tag["Key"] == "version":
                        log.debug(
                            f"""version tag: {tag["Value"]}, version: {__version__}"""
                        )
                        if tag["Value"] == __version__:
                            log.debug("version tag is correct")
                            ok = True
    return ok


def installstack(options):
    try:
        acctid = None
        sess = boto3.session.Session(profile_name=options["profile"])
        acctid = sess.client("sts").get_caller_identity().get("Account")
        log.info(
            f"""profile: {options["profile"]}, account id {acctid}, account name {options["acctname"]}"""
        )
        if acctid is None:
            raise Exception(
                f"""failed to find account id for profile {options["profile"]}"""
            )
        cfn = CFNClient(profile=options["profile"])
        status = cfn.waitForStack(options["stackname"])
        xd = buildStackDict(options)
        if status is not None and "COMPLETE" in status:
            if not checkStack(cfn.stackDetails(options["stackname"])):
                # stack exists, so update it
                log.warning(f"""updating stack {options["stackname"]}""")
                cfn.updateStack(**xd)
                time.sleep(10)
                status = cfn.waitForStack(options["stackname"])
            else:
                log.info(f"""Stack {options["stackname"]} is up to date""")
        elif status is None:
            log.info(f"""creating stack {options["stackname"]}""")
            cfn.createStack(**xd)
            time.sleep(10)
            status = cfn.waitForStack(options["stackname"])
        else:
            msg = f"""stack {options["stackname"]} is status: {status}"""
            log.error(msg)
            raise Exception(msg)
    except ClientError as ce:
        log.warning("Client Error: stack probably already up to date")
        log.warning(f"{ce}")
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


def stackstatus(options):
    try:
        cfn = CFNClient(profile=options["profile"])
        status = cfn.stackStatus(options["stackname"])
        if status is None:
            msg = f"""stack: {options["stackname"]} not found"""
        else:
            msg = f"""stack {options["stackname"]} is status: {status}"""
        log.info(msg)
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


def deletestack(options):
    try:
        cfn = CFNClient(profile=options["profile"])
        status = cfn.waitForStack(options["stackname"])
        if status is not None and "COMPLETE" in status:
            log.warning(f"""deleting stack: {options["stackname"]}""")
            cfn.deleteStack(options["stackname"])
            time.sleep(10)
            status = cfn.waitForStack(options["stackname"])
            msg = f"""stack {options["stackname"]} is status: {status}"""
            log.info(msg)
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


def AllAccounts(options, dothree=False):
    try:
        log.info(f"install-template.py {__version__}")
        log.info("installing / updating to all accounts")
        ch = Chaim("wibble", "wobble")
        accts = ch.requestList()
        del ch
        cn = 0
        for acct in accts:
            cn += 1
            if cn > 2 and dothree:
                break
            if acct[0] == "324919260230":
                log.info("Checking billing account")
                options["profile"] = "awsbilling"
                options["acctname"] = "Connected Homes"
                installstack(options)
            else:
                options["profile"] = "tempname"
                with Chaim(acct[1], "apu", 1) as success:
                    if success:
                        options["acctname"] = acct[1]
                        # makePackage("tempname", acct[0])
                        # stackstatus(stackname, profile="tempname")
                        installstack(options)
                    else:
                        msg = f"failed to obtain creds for account {acct[1]}"
                        raise Exception(msg)
            # break
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


def whichAction(actions):
    """ checks that one, and only one is set True
    """
    try:
        action = []
        for act in actions:
            if actions[act]:
                action.append(act)
        cn = len(action)
        if cn == 0:
            raise Exception("No action requested - try '-h' for help.")
        elif cn > 1:
            raise Exception(f"Too many actions requested: '{action}'")
        return action[0]
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


def testOptions(action, opts, musthave):
    try:
        missing = []
        for opt in musthave:
            if not opts[opt]:
                missing.append(opt)
        if len(missing) > 0:
            msg = f"""{action} action requires these options:
            {musthave}
            These were missing from the input:
            {missing}
            """
            raise Exception(msg)
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


def setupInput():
    try:
        lactions = ["install", "delete", "status", "all"]
        lopts = ["acctname", "stackname", "profile", "params", "templatefn", "product"]
        sdopts = ["stackname", "profile"]
        aopts = ["stackname", "params", "templatefn", "product"]
        actions = {}
        musthave = {}
        for action in lactions:
            actions[action] = False
        options = {}
        for option in lopts:
            options[option] = None
        musthave["install"] = lopts
        musthave["delete"] = sdopts
        musthave["status"] = sdopts
        musthave["all"] = aopts
        return (actions, options, musthave)
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


@getopt2(sys.argv[1:], "a:ADhIM:n:p:P:St:")
def main(opts: List[Tuple]):
    try:
        actions, options, musthave = setupInput()
        cnopts = 0
        for opt, arg in opts:
            if opt == "-A":
                actions["all"] = True
            elif opt == "-a":
                options["acctname"] = arg
                cnopts += 1
            elif opt == "-D":
                actions["delete"] = True
            elif opt == "-h":
                usage()
            elif opt == "-I":
                actions["install"] = True
            elif opt == "-m":
                options["params"] = arg
                cnopts += 1
            elif opt == "-n":
                options["stackname"] = arg
                cnopts += 1
            elif opt == "-p":
                options["product"] = arg
                cnopts += 1
            elif opt == "-P":
                options["profile"] = arg
                cnopts += 1
            elif opt == "-S":
                actions["status"] = True
            elif opt == "-t":
                options["templatefn"] = arg
                cnopts += 1
        action = whichAction(actions)
        testOptions(action, options, musthave[action])
        if action == "all":
            # AllAccounts(options, dothree=True)
            AllAccounts(options)
        elif action == "delete":
            deletestack(options)
        elif action == "install":
            installstack(options)
        elif action == "status":
            stackstatus(options)
        else:
            raise Exception(f"Unknown action {action}")
    except Exception as e:
        fname = sys._getframe().f_code.co_name
        errorExit(fname, e)


if __name__ == "__main__":
    main()
