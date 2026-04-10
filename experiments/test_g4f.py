from g4f.client import Client

client = Client()
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'hello world'"}],
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
