import hashlib
from mixpanel import Mixpanel

mp = Mixpanel('your-mixpanel-token-goes-here')

BASIC_RESPONSE = {
    "speech": "Say something sensible",
    "displayText": "",
    "data": {},
    "contextOut": [],
    "source": "Bilbobot"
}

def log_mixpanel_event(user_id, intent):
    hashed_id = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    mp.track(hashed_id, 'Intent Fired', {
        'Intent name': intent
    })
    

def intent_handler(intent):
    if intent == 'capital_weather':
        response = 'Use the weather shazam app from T Ulman show'
    elif intent == 'capital_time':
        response = 'Get yourself a watch'
    elif intent == 'knock_knock':
        response = 'Who\'s there?'
    else:
        response = 'Nada!'
    return response


def lambda_handler(event, context):
    reply = BASIC_RESPONSE
    intent = event['result']['metadata']['intentName']
    user_id = event['originalRequest']['data']['actorId']
    speech = intent_handler(intent)
    reply['speech'] = 'Your id is: {}\nIntent identified as:{}\n{}'\
        .format(user_id, intent, speech)
    # Now call the Mixpanel API
    log_mixpanel_event(user_id, intent)
    print(event)
    return reply