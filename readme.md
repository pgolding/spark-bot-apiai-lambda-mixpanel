## API.AI Bot Handler AWS Lambda/Mixpanel

This is a very rudimentary setup (i.e. minimal code for clarity and no error handling) to create a bot for Cisco Spark that relies on API.AI for NLP and Mixpanel for metrics. The flow is roughly as shown below.

![image](https://cloud.githubusercontent.com/assets/28526/23763455/8f72e4b4-04ae-11e7-81f0-0f9101984c9e.png)

To set up a bot on Cisco Spark that relies on API.AI for the NLP and Mixpanel for metrics, do the following:

### 1. Create a Bot on Cisco Spark ###


Go visit the [Spark Developer Portal](https://developer.ciscospark.com/apps.html) and create a bot. You can name it how you like and the name really doesn't matter (apart from it's uniqueness on the Spark platform)

You will need a 512x512 PNG icon file, which you can host somewhere like S3 (with public read access)

That's all you need for now because we will rely on API.AI to create the [webhook](https://developer.ciscospark.com/webhooks-explained.html) that will handle messages to your bot. Note that our plan here is to wire Spark to API.AI and then use an AWS Lambda function (here in Python) to process the NLP-parsed messages.

Copy the Access Token for this bot as you will need it to wire API.AI to your bot.

As a brief explanation of what's going on here, when you create a bot on Spark it is similar to creating a user account. In effect, a bot is acting like a "person" on the platform. However, the platform registers your bot with its API layer so that it can push/pull messages via the API. The access token is how any API calls are associated with your bot.

### 2. Create an agent on API.AI ###

Create an agent on API.AI and "train" it:

* Create some intents and train them
* Label the intents (e.g. weather_intent, time_intent, knock_knock)
* Click on the SHOW JSON button to see an intent record processed by API.AI. It will look something like:

```json
{
  "id": "0566f506-c716-46e8-b193-0e009ddefcab",
  "timestamp": "2017-03-09T05:30:05.838Z",
  "lang": "en",
  "result": {
    "source": "agent",
    "resolvedQuery": "tell me my sales for today",
    "action": "get_sales",
    "actionIncomplete": false,
    "parameters": {},
    "contexts": [],
    "metadata": {
      "intentId": "2ca045d3-2eb9-4cc2-81b2-1c3db150da58",
      "webhookUsed": "true",
      "webhookForSlotFillingUsed": "false",
      "intentName": "sales_query"
    },
    "fulfillment": {
      "messages": [
        {
          "type": 0,
          "speech": ""
        }
      ]
    },
    "score": 1
  },
  "status": {
    "code": 200,
    "errorType": "success"
  },
  "sessionId": "83b14187-06db-4a4b-9763-9592c8c2d821"
}
```

This JSON object will be passed by API.AI to your bot handler on AWS (see diagram above) once we wire things up. 

### 3. Wire your API.AI agent to your bot ###

For your agent project on API.AI, visit the integrations tab on the left and enable the Cisco Spark integration. Click on SETTINGS on the Cisco Spark element to bring up the modal into which you should paste your bot Access Token that you copied from Step 1.

![screenshot 2017-03-09 10 08 25](https://cloud.githubusercontent.com/assets/28526/23763969/a347d178-04b0-11e7-9644-15b931989017.png)

What this step does is enable API.AI to register a [webhook](https://developer.ciscospark.com/webhooks-explained.html) on Spark for your bot. The webhook will send the events from your bot to the API.AI platform at an address something like: https://bots.api.ai/spark/GUID/webhook

If you are curious about the webhook configuration (and in case you ever want to delete it) you can visit the interactive API documentation for webhooks on the Spark portal and paste in your Access Token to make a GET request to see the webhook registration that API.AI just made:

![screenshot 2017-03-09 10 17 15](https://cloud.githubusercontent.com/assets/28526/23764277/cffab428-04b1-11e7-9f08-a940f72b11f4.png)

Now that you have completed this step, any interactions with your bot on Spark will be forward via this webhook to the API.AI system. The GUID in the API.AI address enables API.AI to associate all such messages with the agent you just created.

### 4. Create an AWS Lambda Function ###

What you have done so far is to create a bot and wire it up to an agent on API.AI. That agent can now interpret messages sent to your bot and try to recognize intents. These intents now need to be processed so that the agent knows how you want to respond to the intents. 

For example, if a user asks the bot: "What are my sales today?" then the API.AI system can be trained to recognize this utterance (and others like it) as an intent to discover sales for a certain interval ("today").

Your agent would interpret such utterances and map them to an intent, say ```sales_intent```, that will be passed as a field in the JSON object (see above example) that API.AI forwards to your Lambda Function.

Let's now set up that Lambda Function (LF).

Login to or create your account on AWS. Go to Lambda and create a function using a blank template and setting the language to Python (for this example).

Copy and paste the following code into your function:

```python
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
```

Because this is an AWS LF, you won't see any code here to handle requests (e.g. via an HTTP library or such). The LF is fired whenever its URL is activated (e.g. via a POST request from API.AI) and the default configuration of the LF is to look for a file called lambda_function.py (which you just edited) and then pass the body of the request into a handler ```lambda_handler``` via the variable ```event```.

In other words, this ```event``` variable should contain the JSON object (see above) from API.AI whenever it interprets an intent for your agent.

In this simple example, we simply extract the intent field from the JSON:

```python
intent = event['result']['metadata']['intentName']
```

And we pass this to our own ```intent_handler``` to do something with it. In this case, we return as string 'Your sales are healthy' when we see the intent ```get_sales```

API.AI expects a certain JSON object as the returned response and that's what you see with ```BASIC_RESPONSE```. After overwriting the "speech" field with our return string, we merely return this entire object from the ```lambda_handler``` in order to respond to the inbound webhook request from API.AI.

What we need to do now is to wire up the API.AI agent with our LF.

