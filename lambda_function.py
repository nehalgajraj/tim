import json
import openai
import boto3
import os
from datetime import datetime

# Initialize the DynamoDB resource
dynamodb = boto3.resource('dynamodb')

def get_conversation(phone):
    table = dynamodb.Table('conv_hoi')
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(phone),
        ScanIndexForward=True
    )
    return response['Items']

def store_message(user_id, sender, content):
    table = dynamodb.Table('conv_hoi')
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    message_id = f'{user_id}-{timestamp}'
    
    response = table.put_item(
        Item={
            'user_id': user_id,
            'timestamp': timestamp,
            'message_id': message_id,
            'sender': sender,
            'content': content
        }
    )
    return response
    
    
def read_system_message(file_path):
    with open(file_path, 'r') as file:
        content = file.read().strip()
    return content

def lambda_handler(event, context):
    
    model_to_use = "gpt-3.5-turbo"
    openai.api_key = os.environ['openai_api_key']

    # Extract the user_message and phone number from the event object
    user_message = json.loads(event['body'])
    phone_number = user_message['phone']
    message_content = user_message['user_message']
    
    # Fetch the conversation history
    conversation_history = get_conversation(phone_number)
    
    # Check my phone number
    if phone_number == "447405377827":
        system_message_content = read_system_message('system_message_self.txt')
    else:
        system_message_content = read_system_message('system_message.txt')
    
    
    # Format conversation history for OpenAI API
    messages = [{"role": "system", "content": system_message_content}]
    for message in conversation_history:
        role = message['sender']
        content = message['content']
        messages.append({"role": role, "content": content})
    
    # Add the current user message to the messages list
    messages.append({"role": "user", "content": message_content})
    
    response = openai.ChatCompletion.create(
        model=model_to_use,
        messages= messages,
        temperature=0.7,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    
    text_response = response['choices'][0]['message']['content'].strip()

    # Save the user's message and the assistant's response to the DynamoDB table
    store_message(phone_number, 'user', message_content)
    store_message(phone_number, 'assistant', text_response)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'response': text_response
        })
    }
