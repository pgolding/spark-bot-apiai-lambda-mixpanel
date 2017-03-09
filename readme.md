## API.AI Bot Handler AWS Lambda/Mixpanel

This is a **very rudimentary setup** (i.e. minimal code for clarity and no error handling) to create a bot for Cisco Spark that relies on API.AI for NLP and Mixpanel for metrics - i.e. a full "bot stack" for implementing bots in the wild. I couldn't find any such implementation documented already, plus the various examples (on Cisco/API.AI) often miss simple steps or gloss over any attempt to explain what's going on "under the hood" (which will make it easier for you to build on this example).

My goal is to minimize the coding effort whilst ensuring that the set-up is scalable to production if you wish to pursue bots for your customers. 

The data event flow is roughly as shown below.

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

If you are curious about the webhook configuration (and in case you ever want to delete it) you can visit the [interactive API documentation for webhooks](https://developer.ciscospark.com/endpoint-webhooks-get.html) on the Spark portal and paste in your Access Token to make a GET request to see the webhook registration that API.AI just made:

![screenshot 2017-03-09 10 17 15](https://cloud.githubusercontent.com/assets/28526/23764277/cffab428-04b1-11e7-9f08-a940f72b11f4.png)

Now that you have completed this step, any interactions with your bot on Spark will be forwarded via this webhook to the API.AI system. The GUID in the API.AI address enables API.AI to associate all such messages with the agent you just created.

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

Note that we added a simple print statement that dumps the entire event object to the associated LF logs (stored on Cloud Watch). This is the best way to develop a LF because whenever things go wrong, you can go poke around in the detailed logs.

To test your bot, you need to configure an example event payload. Simply copy the JSON object from above and paste it into the test event (via "Actions > Configure test event" dropdown menu).

![screenshot 2017-03-09 10 56 41](https://cloud.githubusercontent.com/assets/28526/23765837/6b0a4a32-04b7-11e7-80e4-76caf481fd26.png)

What we need to do now is to wire up the API.AI agent with our LF.

### 5. Wire your API.AI agent to your LF ###

We are going to tell API.AI how to send interpreted intents to our LF, but first we need to expose our LF to the internet. I'm assuming that you are interested eventually in deploying a bot for real, so we will take a little time here to expose your LF via the AWS API Gateway Service (GS). This is possibly the trickiest part of the process, but mostly because the GS is a bit awkward to configure if you're not used to it.

Step 1 - Create an API and select "New API" - give it a name, say "bot".

Step 2 - Add a "Method" to your API

![screenshot 2017-03-09 11 01 37](https://cloud.githubusercontent.com/assets/28526/23766418/9392524a-04b9-11e7-855c-ae0200e1797e.png)

We won't give the method a name as we just want to call the API from the '/' at the end of the URL. But let's say you were creating several bots, then you might use the botname here so your API webhooks end with a bot name, like '/salesbot'

Step 3 - Add an action (HTTP Verb) to your method

![screenshot 2017-03-09 11 01 49](https://cloud.githubusercontent.com/assets/28526/23766422/96b00d78-04b9-11e7-8740-60b67a8ccb5e.png)

All we need is a POST for API.AI, so select POST.

Step 4 - Configure your POST to route it to your LF

![screenshot 2017-03-09 11 02 15](https://cloud.githubusercontent.com/assets/28526/23766436/a0bb8bda-04b9-11e7-995a-eb6414058190.png)

Enter whatever name you used for your LF

Step 5 - Deploy your API:

![screenshot 2017-03-09 11 03 06](https://cloud.githubusercontent.com/assets/28526/23766444/a95b0c16-04b9-11e7-96d0-8a8003084518.png)

Give it a deployment stage name, say "dev" (for development) for now.

![screenshot 2017-03-09 11 03 23](https://cloud.githubusercontent.com/assets/28526/23766447/ad8ef414-04b9-11e7-96c8-a22581bbfbe9.png)

That's it!

It you visit the Dashboard link for your API, you will see the external URL to reach this method (that will pass the POST message body as ```event``` to your LF ```lambda_handler``` function).

If you try to load the URL directly in your browser you will get a message like "Missing Authentication Token" which you can ignore because your browser is issuing a GET request (and you need to send a POST). If you want to explore how this works, you can use a tool like Postman and send a POST command to the URL whilst attaching the above JSON as the *raw* body (and selecting ```JSON (application/json)``` as the content type).

Now you're ready to wire your agent to your LF (via this gateway API) by revisiting your agent on API.AI and selecting the "Fulfilment" tab on the left. Here you will see a place to insert your API:

![screenshot 2017-03-09 11 24 30](https://cloud.githubusercontent.com/assets/28526/23766817/264ed9ea-04bb-11e7-8e1b-722d5f8c3dcf.png)

One last thing to complete the wiring. You need to open each intent that you want to be handled by this webhook (i.e your LF) and select the "Use webhook" option under "Fulfillment" at the bottom of the intent page.

![screenshot 2017-03-09 11 28 16](https://cloud.githubusercontent.com/assets/28526/23766953/99f1649e-04bb-11e7-8aa6-5e95e6475acb.png)

### 6. Add Mixpanel Analytics ###

#### A. Setting up Mixpanel and Integrating with your LF ####

Mixpanel tends to emphasize behavioral analytics and so it supports a more event-friendly tracking model. There is no reason that this can't be extended to capture bot interactions. The basic "unit of interaction" for a bot would seem to be the recognition of an intent. Therefore, it makes sense to track intents as a kind of behavioral record that should tell us the kinds of interactions, problems and interests that users explore with our bot.

First, you need to install the Mixpanel Python library. However, you need to do this in a way that enables us to upload the library with our LF code to AWS Lambda Service because the standard Python environment on AWS only extends to all of the standard Python libraries plus the Amazon SDK (Boto3).

Create an empty folder (say with your bot name as the folder name) and then open a terminal at that same path.

At the command line and **at the path where your LF code will reside on your machine**, use PIP to install it in the following way:

>pip install Mixpanel -t .

This should create the Mixpanel folder in your local folder. You will also see another folder (ending "-info") and perhaps a file called six.py

Go to Mixpanel and create a project for your bot, say with the same name as your bot. Once created, there is nothing else for you to do except go to the "Project Settings" via the dropdown upper right (where your login name is displayed) and copy the Token field.

Now create a file called ```lambda_function.py``` in your folder and paste in the code from the file of the same name in this repo. It is very similar to the code above, except that we've added a few things.

First we import the library and then set up the Mixpanel object (using your Mixpanel token for this project):

```python
import Mixpfrom mixpanel import Mixpanel
mp = Mixpanel('your-mixpanel-token-goes-here')
```

Then we use a simple function to send events to Mixpanel:

```python
def log_mixpanel_event(user_id, intent):
    hashed_id = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    mp.track(hashed_id, 'Intent Fired', {
        'Intent name': intent
    })
```

This code adds an event to Mixpanel by calling the Mixpanel.track() method. This accepts three arguments:
* A distinct user ID (known as DistinctID on Mixpanel)
* An event name (here called 'Intent Fired')
* Event properties (that can be used to segment events in Mixpanel)

It will be useful to tie bot users back to identities on the Spark platform so that we know a bit more about who is using our bot. To do this, we can access data about the Spark user who interacted with the bot via some additional JSON fields attached to the above JSON object. These fields are nested beneath an object called 'originalRequest' which is accessible via the inbound event to our LF:

```python
user_id = event['originalRequest']['data']['actorId']
```

Here we extract the user ID of the user who addressed the bot (known as the "actor" on Spark platform, hence "actorId"). Note that there are various useful fields in this augmented object, such as the room ID and even the user's public identity (e.g. email and/or display name). Of course, any of these fields can be added to the mixpanel 'Intent Fired' event as event properties.

We used the extracted ID to pass in as the user's distinct ID on Mixpanel. We should use this every time we log an event so that we can segment events in Mixpanel by user (in the way Mixpanel expects to work).

Note that in order to obscure the user's Spark ID, we are hashing the ID (using SHA256) to protect user identities whilst storing in a 3rd-party analytics system. You should understand the importance of storing customer data and assume the risk accordingly.

#### B. Deploying LF with Mixpanel Integration ####

You can't just paste your new Python code into the LF inside the AWS Lambda Console because you now need to deploy the Mixpanel library that you just installed locally with PIP.

You will need to ZIP and upload your code with the library.

To do this, navigate **inside** of the folder and compress the following files and folder ('mixpanel')

> lambda_function.py

> six.py

> mixpanel

Compress these three items. Do not compress the folder that contains these three items!!

Now go to the AWS Lambda console for your function and select the code tab and then select "Upload a .ZIP file" via the "Code entry type" dropdown above the code window.

![screenshot 2017-03-09 12 20 27](https://cloud.githubusercontent.com/assets/28526/23769023/cdff0320-04c2-11e7-8162-3d547c06fca8.png)

The click "Save". Don't worry if the test fails because the JSON object you originally put into the test harness is lacking the augmented 'originalRequest' fields expected by your code.

That's it! Now your code is wired up and ready to send events to mixpanel.

#### C. Testing Mixpanel Integration ####

This is the exciting part. Navigate to your Mixpanel project for the bot and open the "Live view" on the left had side navigation.

![screenshot 2017-03-09 12 17 06](https://cloud.githubusercontent.com/assets/28526/23768917/713a0f4a-04c2-11e7-8b8d-77a9cf7aa211.png)

Now start sending messages to your bot via your Spark client. Of course, my script assumes I created an intent called ```sales_intent``` that is triggered by phrases like "What are my sales today?"

If I type this into Spark, I get the default feel-good answer from my script "Your sales are looking good", but I also see an event fire in the live view.

For my example (not all shown here) I created a few intents with different names. If I open the Segmentation view inside of Mixpanel, I can now see these events and, furthermore, segment by Intent name (which was a property I sent in) to see which types of interaction are popular with my bot.

![screenshot 2017-03-09 12 17 39](https://cloud.githubusercontent.com/assets/28526/23768926/76086616-04c2-11e7-8700-1bf8d1fba888.png)

You can imagine feeding in a whole bunch of properties to make segmentation interesting. Also, if you set up more complex bot dialog interactions (multi-event) then you can go ahead and create funnels to see how far users get in traversing such dialogs.

As an additional feature, if your bot sends interactions in the results, such as weblinks (e.g. to sales reports, help docs etc.) then you should consider instrumenting those destinations (websites) using Mixpanel and sending the events to the same project. This will enable you to view entire user journies from inside your bot interaction to external web-based (or other app) interactions.

There are all kinds of ways to think about bot analytics here that would serve to produce quality behavioral insights. You should consider how you test that effectiveness of the interaction UX.

### What next? ###

This is a minimal bot implementation with an emphasis on getting you started with a bot whilst at least putting into place all the elements to enable you to scale it out to production. What's remarkable is how little code is required to get an entire bot/agent/analytics stack going. And, thanks to AWS LF, it's scalable.

If you were building this out as a production-ready bot, then you'd need to consider the following things:

1. Extensive training of the API.AI agent (see their docs)
2. Robust Python implementation (exception handling, logging etc.)
3. Robust API protection (add an API key to your API GS and add this to the webhook)
4. Avoiding bare (Mixpanel) tokens in the Python code (use the AWS key encryption service KMS)
5. Thorough event/property definition for your Mixpanel events
6. More comprehensive handling of the intents in your LF (optimized for AWS LF patterns)
7. Structured maintenance of your bot responses (e.g. in a content management system)
8. Implement A/B testing (lots of options to explore here)

For thos of you interested in creating a Cisco Spark bot entirely on AWS (i.e. without API.AI NLP) then I have a template for doing that, including an asynchronouse fan-out LF to offload the response and follow the "single unit of work" pattern for AWS Lambda. I plan to publish it soon along with a test harness for developing your LF locally and uploading automatically to AWS whenever you want to integrate.






