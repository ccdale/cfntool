cfntool
=======

A tool to Create and Delete Cloudformation stacks easily.
Uses credentials from your `~/.aws/credentials` file via boto3

Install
-------

::

  $ python3 -m pip install cfntool --user


Usage
-----

::

  cfn [-options]

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

Examples
--------

Create a stack from a yaml template::

  $ cfn -I -p mytool -P myaccountalias -m myaccount -n myStackName \
      -t ~/src/mystack.yaml -m 'LambdaVersion=0.0.2,Owner=SRE'

  06/03/2020 08:40:05 [INFO ]  profile: myaccountalias, account id 1234567890, account name myaccount
  06/03/2020 08:40:06 [ERROR]  stack: myStackName does not exist
  06/03/2020 08:40:06 [WARNI]  stack myStackName does not exist (anymore)
  06/03/2020 08:40:06 [INFO ]  creating stack myStackName
  06/03/2020 08:41:47 [INFO ]  Stack myStackName is CREATE_COMPLETE


Status of named stack::

  $ cfn -S -P myaccountalias -n myStackName

  06/03/2020 08:42:14 [INFO ]  stack myStackName is status: CREATE_COMPLETE

Delete a stack::

  $ cfn -D -P myaccountalias -n myStackName

  06/03/2020 08:44:39 [INFO ]  Stack myStackName is CREATE_COMPLETE
  06/03/2020 08:44:39 [WARNI]  deleting stack: myStackName
  06/03/2020 08:46:20 [ERROR]  stack: myStackName does not exist
  06/03/2020 08:46:20 [WARNI]  stack myStackName does not exist (anymore)
  06/03/2020 08:46:20 [INFO ]  stack myStackName is status: None
