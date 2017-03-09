BASIC_RESPONSE = {
    "speech": "Say something sensible",
    "displayText": "",
    "data": {},
    "contextOut": [],
    "source": "my_bot_name_on_aws"
}

def intent_handler(intent):
    if intent == 'get_sales':
        response = 'Your sales are healthy'
    else:
        response = 'Nada!'
    return response


def lambda_handler(event, context):
    reply = BASIC_RESPONSE
    intent = event['result']['metadata']['intentName']
    speech = intent_handler(intent)
    reply['speech'] = response
    # This print is for logging purposes
    print(event)
    return reply