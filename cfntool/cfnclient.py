import sys
import time
from cfntool.botosession import BotoSession
from cfntool.errors import errorRaise
from botocore.exceptions import ClientError
import ccalogging

log = ccalogging.log


class CFNClient(BotoSession):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.newClient("cloudformation")

    def stackDetails(self, stackname):
        try:
            resp = self.client.describe_stacks(StackName=stackname)
            if "Stacks" in resp:
                stack = resp["Stacks"][0]
                return stack
        except ClientError as ce:
            log.error(f"stack: {stackname} does not exist")
            return None
        except Exception as e:
            fname = sys._getframe().f_code.co_name
            errorRaise(fname, e)

    def stackStatus(self, stackname):
        try:
            stack = self.stackDetails(stackname)
            return stack["StackStatus"] if stack is not None else None
        except Exception as e:
            fname = sys._getframe().f_code.co_name
            errorRaise(fname, e)

    def createStack(self, **kwargs):
        try:
            resp = self.client.create_stack(**kwargs)
            if "StackId" in resp:
                return resp["StackId"]
            return None
        except Exception as e:
            fname = sys._getframe().f_code.co_name
            errorRaise(fname, e)

    def updateStack(self, **kwargs):
        try:
            resp = self.client.update_stack(**kwargs)
            if "StackId" in resp:
                return resp["StackId"]
            return None
        except Exception as e:
            fname = sys._getframe().f_code.co_name
            errorRaise(fname, e)

    def deleteStack(self, stackname):
        try:
            self.client.delete_stack(StackName=stackname)
        except Exception as e:
            fname = sys._getframe().f_code.co_name
            errorRaise(fname, e)

    def waitForStack(self, stackn, timeout=10, sleeptime=30):
        """ wait for a stack to become "..._COMPLETE"

        waits for timeout * sleeptime seconds

        returns the stack status
        """
        try:
            waiting = True
            status = None
            cn = 0
            sleeptime = 30
            while waiting:
                cn += 1
                if cn > timeout:
                    log.error(
                        f"Timeout expired waiting for stack {stackn} to become ready"
                    )
                    waiting = not waiting
                    break
                status = self.stackStatus(stackn)
                if status is not None and "COMPLETE" in status:
                    log.info(f"Stack {stackn} is {status}")
                    waiting = not waiting
                    break
                elif status is None:
                    log.warning(f"stack {stackn} does not exist (anymore)")
                    waiting = not waiting
                    break
                time.sleep(sleeptime)
            return status
        except Exception as e:
            fname = sys._getframe().f_code.co_name
            errorRaise(fname, e)
