from elasticsearch import Elasticsearch
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import os

# Determine if running in Docker container or locally
running_in_docker = os.environ.get("DOCKER_ENV", False)

# Connection to the cluster
if running_in_docker:
   es = Elasticsearch(hosts="https://elastic:datascientest@application-es01-1:9200",
                       verify_certs=False)
else:
   es = Elasticsearch(hosts="https://elastic:datascientest@localhost:9200",
                       ca_certs="./ca/ca.crt")

# Initialize the VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Define the search query to retrieve all documents
search_query = {
    "query": {
        "match_all": {}
    },
    "size": 100  # Number of documents per page
}

# Define the base directory based on where the script is located
base_dir = os.path.dirname(os.path.abspath(__file__))

# OUTPUT ALL REVIEWS WITH SENTIMENT

# Lists to store data
review_ids = []
company_ids = []
company_names = []
review_texts = []
compound_scores = []
sentiment_labels = []

# Initialize the Scroll API
scroll_query = search_query
scroll_query["scroll"] = "5m"  # Set the scroll time, adjust as needed

# Paginated search using the Scroll API
scroll_id = None
while True:
    if scroll_id is None:
        response = es.search(index="bestatm_reviews", scroll="5m", body={"query": {"match_all": {}}, "size": 100})
    else:
        response = es.scroll(scroll_id=scroll_id, scroll="5m")
    
    scroll_id = response.get("_scroll_id")
    hits = response["hits"]["hits"]
    
    if not hits:
        break
    
    for hit in hits:
        source = hit.get("_source", {})
        review_id = source.get("review_id", "")
        company_id = source.get("company_id", "")
        company_name = source.get("company_name", "")
        review_text = source.get("review_text", "")
        
        if review_text:
            sentiment_scores = analyzer.polarity_scores(review_text)
        
            compound_score = sentiment_scores["compound"]
            if compound_score >= 0.05:
                sentiment_label = "Positive"
            elif compound_score <= -0.05:
                sentiment_label = "Negative"
            else:
                sentiment_label = "Neutral"
            
            review_ids.append(review_id)
            company_ids.append(company_id)
            company_names.append(company_name)
            review_texts.append(review_text)
            compound_scores.append(compound_score)
            sentiment_labels.append(sentiment_label)

# Clear the scroll context when done
es.clear_scroll(scroll_id=scroll_id)

# Create dictionary
data_all = {
    "ReviewID": review_ids,
    "CompanyID": company_ids,
    "CompanyName": company_names,
    "ReviewText": review_texts,
    "SentimentScores": compound_scores,
    "SentimentLabel": sentiment_labels
}

# Create DataFrame
df_all = pd.DataFrame(data_all)

# Output DataFrame to a CSV file
output_csv_path = os.path.join(base_dir, "output", "reviews_sentiments.csv")
df_all.to_csv(output_csv_path, index=False)

# COUNT MOST USED WORDS 

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter


# Tokenize and process reviews to find most common words
nltk.download('punkt')
nltk.download('stopwords')

# Combine all review texts into one string
all_reviews_text = ' '.join(df_all['ReviewText'])

# Tokenize words
words = word_tokenize(all_reviews_text)

# Remove stopwords
stop_words = set(stopwords.words("english"))
filtered_words = [word for word in words if word.lower() not in stop_words and len(word) > 2]

# Count the frequency of words
word_counts = Counter(filtered_words)

# Get the most common words (change the number as needed)
most_common_words = word_counts.most_common(20)

# Print the most common words
#print("Most common words in reviews:")
#for word, count in most_common_words:
#    print(f"{word}: {count}")

#CREATE WORD BUCKETS AND OUTPUT WORD ANALYSIS

# Define the word buckets
word_buckets = {
    "bank account": ["bank", "account"],
    "customer service": ["customer", "service"],
    "credits": ["loan", "credit"]
}

# Initialize dictionary to store values for the new DataFrame
new_data = {
    "SentimentScores": [],
    "SentimentLabel": [],
    "CompanyName": [],
    "CompanyID": []
}
for bucket in word_buckets.keys():
    new_data[bucket] = []

# Iterate over each row in the DataFrame
for index, row in df_all.iterrows():
    new_data["SentimentScores"].append(row["SentimentScores"])
    new_data["SentimentLabel"].append(row["SentimentLabel"])
    new_data["CompanyName"].append(row["CompanyName"])
    new_data["CompanyID"].append(row["CompanyID"])
    review_text = row["ReviewText"].lower()
    word_counts = Counter(review_text.split())  # Count words in the review text
    
    for bucket, words in word_buckets.items():
        bucket_count = sum(word_counts.get(word, 0) for word in words)
        new_data[bucket].append(bucket_count)

# Create the new DataFrame
df_new = pd.DataFrame(new_data)

# Display the new DataFrame
#print(df_new)

# Output DataFrame to a CSV file
word_analysis_csv_path = os.path.join(base_dir, "output", "word_analysis.csv")
df_new.to_csv(word_analysis_csv_path, index=False)
