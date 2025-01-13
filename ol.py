import ollama
import tiktoken
import time

def count_tokens(text):
    tokenizer = tiktoken.get_encoding("cl100k_base")  # Replace with the correct tokenizer for the model
    return len(tokenizer.encode(text))

# Start tracking time
start_time = time.time()

# Interact with the model
response = ollama.chat(
    model='llama3.1',
    messages=[{
        'role': 'user',
        'content': ' on type of rest position',
    }]
)

# Calculate the duration
end_time = time.time()
elapsed_time = end_time - start_time

# Extract response text
response_text = response.message.content  # Adjust based on the actual response structure

# Count tokens manually
input_prompt = 'generate large text on type of rest position'
input_tokens = count_tokens(input_prompt)
output_tokens = count_tokens(response_text)
total_tokens = input_tokens + output_tokens

# Tokens per minute
tokens_per_minute = (total_tokens / elapsed_time) * 60 if elapsed_time > 0 else 0

print(response)
