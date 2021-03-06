from text_summarizer import wrap_summary
from app.irsystem.controllers.case_ranking import rank_cases
import math
import json
import numpy as np
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from . import *
from app.irsystem.models.helpers import *
from app.irsystem.models.helpers import NumpyEncoder as NumpyEncoder
import os
import time
from flask import current_app
from app import app
import scipy.spatial.distance
from django.utils.safestring import mark_safe 
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer
from nltk.corpus import stopwords
import string
from sklearn.metrics.pairwise import cosine_similarity  
print(os.getcwd())

project_name = "Can I Sue?"
net_id = "Junan Qu (jq77), Zachary Shine (zs92), Ian Paul (ijp9), Max Chen (mlc294), Nikhil Saggi (ns739)"

# r = requests.get(
#     "https://storage.googleapis.com/can_i_sue_reddit/reddit_data.json")
# data = r.json()
# doc_by_vocab = []
# doc_by_vocab_flag = False
# tfidf_vec = TfidfVectorizer(min_df=.01,
#                             max_df=0.8,
#                             max_features=5000,
#                             stop_words='english',
#                             norm='l2')
# print("loaded reddit info ")


# =====REDDIT COSINE======

# title, id, selftext, url, created_utc e60m7


# def get_sim(q_vector, post_vector):
#     num = q_vector.dot(post_vector)
#     den = np.multiply(np.sqrt(q_vector.dot(q_vector)),
#                       np.sqrt(post_vector.dot(post_vector)))
#     return num/den


# =====END=======


@irsystem.route('/about.html')
def go_to_about():
    return render_template('about.html')


@irsystem.route('/', methods=['GET'])
def search():
    # global doc_by_vocab
    # global doc_by_vocab_flag
    # global tfidf_vec
    with app.app_context():
        data = current_app.data
        tfidf_vec = current_app.tfidf_vectorizer
        doc_by_vocab = current_app.tfidf_matrix

    # Search Query
    query = request.args.get('search')
    # Jurisdiction level ('Federal' or state abbreviation)
    jurisdiction = request.args.get('state')
    minimum_date = request.args.get('earliestdate')
    suing = request.args.get('sue-status')
    ncases = request.args.get('quantity')
    print(query)
    print(jurisdiction)
    print(minimum_date)
    print(suing)
    output_message = ''
    if not query:
        res = []
        output_message = ''
        print('no query')
        return render_template('search.html', name=project_name, netid=net_id, output_message=output_message, data=res)
    else:
        query = query.lower()
        query = query.translate(str.maketrans('', '', string.punctuation))
        print('preprocessed query')
        # =====Reddit cos processing START=========
        # title, id, selftext, url, created_utc e60m7
        num_posts = len(data)
        index_to_posts_id = {index: post_id for index,
                                post_id in enumerate(data)}

        # if doc_by_vocab_flag==False:
        #     # d_array = [str(data[d]['selftext'])+str(data[d]['title']) for d in data]
        #     d_array = []
        #     for d in data:
        #         s = str(data[d]['selftext'])+str(data[d]['title'])
        #         d_array.append(s)
        #     doc_by_vocab = tfidf_vec.fit_transform(d_array).toarray()
        #     doc_by_vocab_flag=True

        post_vector = tfidf_vec.transform([query]).toarray()[0]
        start = time.time()
        sims = cosine_similarity([post_vector], doc_by_vocab).reshape(-1)
        #sims = scipy.spatial.distance.cdist(doc_by_vocab, [post_vector], 'cosine').reshape(-1)
        end = time.time()
        print('Reddit cosine Time elapsed: ', str(end - start))
        # quit()
        sim_posts = []
        for i in range(len(sims)):
            score = sims[i]
            if np.isnan(score):
                score = 0.0
            else:
                # print(score)
                score = round(score * 100.0, 3)
                #print(score)
            sim_posts.append((score, i))
        
        print('calculated similarities')
        sim_posts.sort(key=lambda x: x[0], reverse=True)
        print('sorted similarities')

        status = 50

        res = []
        for k in range(25):
            e = data[index_to_posts_id[sim_posts[k][1]]]
            e.update({"score": round(sim_posts[k][0], 1)})
            res.append(e)
        print('added results')
        # =====Reddit cos processing END=========
        print('retrieved reddit cases')
        # =====CaseLaw Retrieval=====
        print('begin caselaw retrieval')
        start = time.time()
        caselaw, debug_msg = rank_cases(
            query, jurisdiction=jurisdiction, earlydate=minimum_date)
        end = time.time()
        print('Case retrieval Time elapsed: ', str(end - start))
        error = False
        if not caselaw:
            # API call to CAP failed
            caseresults = [-1]
            error = True
            judgment_rec="Case Law Error Encountered."
        else:
            caseresults = caselaw
            words_in_query = word_tokenize(query)
            words_in_query = set(words_in_query)
            # Score to keep to 3 decimals
            i = 0
            for case in caseresults:
                case['score'] = round(case['score'] * 100.0, 3)
            # caseresults = wrap_summary(caseresults)
                if not case['case_summary']:  # if case has no summary
                    case['case_summary'] = "No case summary found"
                    continue
                case['case_summary'] = case['case_summary'][0:min(
                    1000, len(case['case_summary']))]
                case['case_summary'] = case['case_summary'] + '...'
                
                #Ian's Bold code
                if i < int(ncases):
                    start = time.time()
                    case_summary_bolded = []
                    words_in_case = word_tokenize(case['case_summary'])                
                    for word in words_in_case:
                        if not (word in string.punctuation or word in stopwords.words()) and word in words_in_query:
                            # print(word)
                            case_summary_bolded.append('<b>'+word+'</b>')
                        else:
                            case_summary_bolded.append(word)
                            
                    case['case_summary'] = TreebankWordDetokenizer().detokenize(case_summary_bolded)
                    end = time.time()
                    print('Bolding Iteration Time elapsed: ', str(end - start))
                    i += 1
            # calculate judgment score
            judgment_score = 0
            judgment_rec = ""
            score_limit = 0
            confidence = 0
            for case in caselaw:
                score_limit += case['score']
                if case['case_outcome'] == "plaintiff":
                    judgment_score += case['score']
                    confidence += 1
                elif case['case_outcome'] == "defendant":
                    judgment_score -= case['score']
                    confidence += 1
            confidence *= 100/len(caselaw)
            if suing == "no":
                judgment_score *= -1

            if judgment_score >= -score_limit and judgment_score < -score_limit/4:
                judgment_rec = "Likely to lose! (with {}% confidence)".format(confidence)
            elif judgment_score >= -score_limit/4 and judgment_score <= score_limit/4:
                judgment_rec = "Could go either way (with {}% confidence)".format(confidence)
            elif judgment_score > score_limit/4 and judgment_score <= score_limit:
                judgment_rec = "Likely to win! (with {}% confidence)".format(confidence)
            
            for case in caseresults:
                case['case_outcome'] = case['case_outcome'][0].capitalize() + case['case_outcome'][1:]
            
            

        # =====Processing results================
        print('completed caselaw retrieval')
        for i in range(5):
            post = res[i]
            if (post['selftext'] is not None) and (len(post['selftext'])) > 500:
                post['selftext'] = post['selftext'][0:500] + '...'

        caselaw_message = "Court Cases:"
        output_message = "Discussion Online:"
        print('rendering template..')
        # ============================

        return render_template('search.html', name=project_name, netid=net_id,
                               output_message=output_message, data=res[:25], casedata=caseresults,
                               caselaw_message=caselaw_message,
                               user_query=query, debug_message=debug_msg,
                               judgment_rec=judgment_rec,
                               is_error=error, num_cases=int(ncases))


@irsystem.route('/about', methods=['GET'])
def about():
    return render_template('about.html')