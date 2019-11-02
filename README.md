# suiro tests
## Suiro tests is a easy to use python CLI tool for testing Rest APIs

## installation
Requirements : Python3 or later version

```pip install -r requirements.txt```

## Path 
add a alias in bash-profile 
``export suiro=/path/of/surio``

## Test files format
Create JSON or YAML test files that consist of tests. Each test has these fields. 
- enabled : to enable the test or not. value is a boolean.
- id : some sort of identifier of the test. eg. get-auth-token 
- headers : array of key value pairs of headers. eg. `
      {
      "content-type": "application/json",
      "Authorization": "Basic cHVibGljOg=="
      }
            `
- method : Http methods eg. GET,  POST, PUT, DELETE,  PATCH
- payload : JSON payload for the rest call.

## Running the test
Create a folder for a project specific tests and create test files.For examle if the name of the file is login-test.json 
`suiro test login-test.json`

