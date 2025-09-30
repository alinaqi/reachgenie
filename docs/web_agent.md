Web Agents
Create a Web Agent
Configure all of the settings for a new web agent.

POST
/
v1
/
agents

Try it
​
Headers
​
authorization
string
required
Your API key for authentication.

Example web call usage (client side):


Copy
import { BlandWebClient } from 'bland-client-js-sdk';

const agentId = 'YOUR-AGENT-ID';
const sessionToken = 'YOUR-SESSION-TOKEN';


document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('btn').addEventListener('click', async () => {
        const blandClient = new BlandWebClient(
            agentId,
            sessionToken
        );
        await blandClient.initConversation({
            sampleRate: 44100,
        });
    });
});
​
Body
​
prompt
string
required
Provide instructions, relevant information, and examples of the ideal conversation flow.


Best Practices

Out-of-the-Box Behaviors (Summarized):
Speech pattern: Direct, concise, casual
Spells out symbols, acronyms, abbreviations, percentages, etc. ($4,000,000 -> “four million dollars”)
Asks clarifying questions
Ends call when objective is complete or voicemail is detected
Prompting Tips:
Want to easily test out exactly how your agent will behave?
Try out Agent Testing!
Aim for less than >2,000 characters where possible.
Simple, direct prompts are the most predictable and reliable.
Frame instructions positively:
"Do this" rather than "Don't do this".
Ex. “Keep the conversation casual” rather than “Don’t be too formal”.
This gives concrete examples of what to do, instead of leaving expected behavior open to interpretation.
​
voice
string
Set your agent’s voice - all available voices can be found with the List Voices endpoint.

​
webhook
string
Set a webhook URL to receive call data after the web call completes.

​
analysis_schema
object
Define a JSON schema for how you want to get information about the call - information like email addresses, names, appointment times or any other type of custom data.

In the webhook response or whenever you retrieve call data later, you’ll get the data you defined back under analysis.

For example, if you wanted to retrieve this information from the call:


Copy
"analysis_schema": {
  "email_address": "email",
  "first_name": "string",
  "last_name": "string",
  "wants_to_book_appointment": "boolean",
  "appointment_time": "YYYY-MM-DD HH:MM:SS"
}
You would get it filled out like this in your webhook once the call completes:


Copy
"analysis": {
  "email_address": "johndoe@gmail.com",
  "first_name": "John",
  "last_name": "Doe",
  "wants_to_book_appointment": true,
  "appointment_time": "2024-01-01 12:00:00"
}
​
metadata
object
Add any additional information you want to associate with the call. This can be useful for tracking or categorizing calls.

​
pathway_id
string
Set the pathway that your agent will follow. This will override the prompt field, so there is no need to pass the ‘prompt’ field if you are setting a pathway.

Warning: Setting a pathway will set the following fields to null / their default value - prompt, first_sentence, model, dynamic_data, tools, transfer_list

Set to null or an empty string to clear the pathway.

​
language
string
default:
"ENG"
Select a supported language of your choice. Optimizes every part of our API for that language - transcription, speech, and other inner workings.

Supported Languages and their codes can be found here.

​
model
string
default:
"enhanced"
Select a model to use for your call.

Options: base, turbo and enhanced.

In nearly all cases, enhanced is the best choice for now.


Model Differences

​
first_sentence
string
A phrase that your call will start with instead of a generating one on the fly. This works both with and without wait_for_greeting. Can be more than one sentence, but must be less than 200 characters.

To remove, set to null or an empty string.

​
tools
array
Interact with the real world through API calls.

Detailed tutorial here: Custom Tools

​
dynamic_data
object
Integrate data from external APIs into your agent’s knowledge.

Set to null or an empty string to clear dynamic data settings.

Detailed usage in the Send Call endpoint.

​
interruption_threshold
number
default:
100
Adjusts how patient the AI is when waiting for the user to finish speaking.

Lower values mean the AI will respond more quickly, while higher values mean the AI will wait longer before responding.

Recommended range: 50-200

50: Extremely quick, back and forth conversation
100: Balanced to respond at a natural pace
200: Very patient, allows for long pauses and interruptions. Ideal for collecting detailed information.
Try to start with 100 and make small adjustments in increments of ~10 as needed for your use case.

​
keywords
string[]
default:
"[]"
These words will be boosted in the transcription engine - recommended for proper nouns or words that are frequently mis-transcribed.

For example, if the word “Reece” is frequently transcribed as a homonym like “Reese” you could do this:


Copy
{
  "keywords": ["Reece"]
}
For stronger keyword boosts, you can place a colon then a boost factor after the word. The default boost factor is 2.


Copy
{
  "keywords": ["Reece:3"]
}
​
max_duration
integer (minutes)
default:
30
The maximum duration that calls to your agent can last before being automatically terminated.

Set to null to reset to default.

​
Response
​
status
string
Can be success or error.

​
call_id
string
A unique identifier for the call (present only if status is success).