import math
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from . import *
from app.irsystem.models.helpers import *
from app.irsystem.models.helpers import NumpyEncoder as NumpyEncoder

project_name = "Team Rob's Chili"
net_id = "jq77, zs92, ijp9, mlc294, ns739"


# =====REDDIT COSINE======

# title, id, selftext, url, created_utc e60m7

num_posts = len(data)
index_to_posts_id = {index: post_id for index, post_id in enumerate(data)}


def build_vectorizer(max_features=5000, stop_words="english", max_df=0.8, min_df=10, norm='l2'):
    tfidf_vec = TfidfVectorizer(stop_words=stop_words, norm=norm,
                                max_df=max_df, min_df=min_df, max_features=max_features)
    return tfidf_vec


def get_sim(q_vector, post_vector):
    num = q_vector.dot(post_vector)
    den = np.multiply(np.sqrt(q_vector.dot(q_vector)),
                      np.sqrt(post_vector.dot(post_vector)))
    return num/den


# =====END=======


@irsystem.route('/', methods=['GET'])
def search():
    query = request.args.get('search')
    print(query)
    output_message = ''
    if not query:
        res = []
        output_message = ''
        return render_template('search.html', name=project_name, netid=net_id, output_message=output_message, data=output)
    else:
        # =====Reddit cos processing START=========
        with open("../subreddit_op_scrape.json") as f:
            data = json.loads(f.readlines()[0])
        # title, id, selftext, url, created_utc e60m7
        num_posts = len(data)
        index_to_posts_id = {index: post_id for index,
                             post_id in enumerate(data)}
        n_feats = 5000
        doc_by_vocab = np.empty([len(data), n_feats])
        tfidf_vec = build_vectorizer(n_feats)
        doc_by_vocab = tfidf_vec.fit_transform(
            [str(data[d]['selftext'])+data[d]['title'] for d in data]+[query]).toarray()
        sim_posts = []
        for post_index in range(num_posts):
            score = get_sim(doc_by_vocab[post_index], doc_by_vocab[num_posts])
            sim_posts.append((score, post_index))
        sim_posts.sort(key=lambda x: x[0], reverse=True)
        res = []
        for k in range(10):
            res.append(data[index_to_posts_id[sim_posts[k][1]]])
         # =====Reddit cos processing END=========
        output_message_1 = "Your search: " + query
        if(len(res) >= 3):
            output_message_2 = 'Here are the top 3 related cases'
        else:
            output_message_2 = 'Here are the top {n:.0f} related cases'.format(
                n=len(res))

        output_message = output_message_1+' \n '+output_message_2
        return render_template('search.html', name=project_name, netid=net_id, output_message=output_message, data=res)
