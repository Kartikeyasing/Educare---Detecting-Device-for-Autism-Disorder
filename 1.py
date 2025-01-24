import requests

# Step 1: Fetch the passage
response = requests.get("https://quest.squadcast.tech/api/RA2111003010082/worded_ip")
passage = response.text

# Step 2: Define a mapping from words to digits
word_to_digit = {
    "zero": "0", "one": "1", "two": "2", "three": "3", 
    "four": "4", "five": "5", "six": "6", "seven": "7", 
    "eight": "8", "nine": "9", "point": "."
}

# Step 3: Split the passage into words and find valid number words
words = passage.split()
number_words = []

for word in words:
    if word in word_to_digit:
        number_words.append(word)

# Print all found number words for debugging
print("Number words found in the passage:", number_words)

# Step 4: Find the first valid sequence of 8 words that could represent an IP address
ip_address = ""
for i in range(len(number_words) - 7):  # Check for sequences of 8 words
    sequence = number_words[i:i + 8]
    if all(word in word_to_digit for word in sequence):
        ip_parts = [word_to_digit[word] for word in sequence]
        ip_address = ''.join(ip_parts)
        break  # Stop after finding the first valid sequence

# Step 5: Validate the constructed IP address
if len(ip_address.split('.')) == 4:
    answer = ip_address
else:
    answer = "No valid IP found"

# Print the answer to be submitted
print("The IP address submitted is:", answer)

# Step 6: Prepare the submission
extension_used = "py"  # Assuming the code is in Python
submission_url = f"https://quest.squadcast.tech/api/RA2111003010082/submit/worded_ip?answer={answer}&extension={extension_used}"

# Step 7: Make the submission
submission_response = requests.post(submission_url, data={"code": '''import requests

response = requests.get("https://quest.squadcast.tech/api/RA2111003010082/worded_ip")
passage = response.text
word_to_digit = {
    "zero": "0", "one": "1", "two": "2", "three": "3", 
    "four": "4", "five": "5", "six": "6", "seven": "7", 
    "eight": "8", "nine": "9", "point": "."
}
words = passage.split()
number_words = []
for word in words:
    if word in word_to_digit:
        number_words.append(word)
ip_address = ""
for i in range(len(number_words) - 7):
    sequence = number_words[i:i + 8]
    if all(word in word_to_digit for word in sequence):
        ip_parts = [word_to_digit[word] for word in sequence]
        ip_address = ''.join(ip_parts)
        break
if len(ip_address.split('.')) == 4:
    answer = ip_address
'''})

# Print the submission response
print("Submission response:", submission_response.json())
