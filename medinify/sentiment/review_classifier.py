"""
Text Classifier primarily for medical text.
Currently can use Naive Bayes, Neural Network, or Decision Tree for sentiment analysis.
"""

import csv
import random
import pickle
import numpy as np
import pandas as pd
from nltk.classify import NaiveBayesClassifier
from nltk.classify import DecisionTreeClassifier
import nltk.classify.util
from nltk.corpus import stopwords
from nltk import RegexpTokenizer
from sklearn.model_selection import StratifiedKFold
from keras.models import Sequential
from keras.layers import Dense, Dropout
import sklearn.preprocessing as process
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import RandomForestClassifier


class ReviewClassifier():
    """For performing sentiment analysis on drug reviews

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.

    """
    classifier_type = None  # 'nb', 'dt', 'nn', 'rf'
    iterations = 10
    negative_threshold = 2.0
    positive_threshold = 4.0
    seed = 123

    model = None

    def __init__(self, classifier_type=None):
        self.classifier_type = classifier_type

    def build_dataset(self, reviews_filename):
        """ Builds dataset of labelled positive and negative reviews

        :param reviews_path: CSV file with comments and ratings
        :return: dataset with labeled positive and negative reviews
        """

        reviews = []
        with open(reviews_filename, newline='') as reviews_file:
            reader = csv.DictReader(reviews_file)

            for row in reader:
                reviews.append({
                    'comment': row['comment'],
                    'rating': row['rating']
                })

        # Separate reviews based on rating
        positive_comments = []
        negative_comments = []

        for review in reviews:
            comment = review['comment']
            rating = review['rating']

            # Make lowercase
            comment = comment.lower()

            # Remove punctuation and tokenize
            tokenizer = RegexpTokenizer(r'\w+')
            word_tokens = tokenizer.tokenize(comment)

            # Remove stopwords and transform into BOW representation
            stop_words = set(stopwords.words('english'))
            filtered_tokens = {
                word: True for word in word_tokens if word not in stop_words
            }

            if float(rating) <= self.negative_threshold:
                negative_comments.append((filtered_tokens, 'neg'))
            if float(rating) >= self.positive_threshold:
                positive_comments.append((filtered_tokens, 'pos'))

        print("Total Negative Instances:" + str(len(negative_comments)))
        print("Total Positive Instances:" + str(len(positive_comments)))

        dataset = positive_comments + negative_comments

        if self.classifier_type == 'nb' or self.classifier_type == 'dt':
            return dataset

        # Vectorize the BOW with sentiment reviews
        vectorizer = DictVectorizer(sparse=False)
        data_frame = pd.DataFrame(dataset)
        data_frame.columns = ['data', 'target']

        data = np.array(data_frame['data'])
        train_data = vectorizer.fit_transform(data)

        target = np.array(data_frame['target'])
        encoder = process.LabelEncoder()
        train_target = encoder.fit_transform(target)

        return train_data, train_target

    def create_trained_model(self,
                             dataset=None,
                             train_data=None,
                             train_target=None):
        """ Creates and trains new model

        Args:
            dataset: dataset with reviews and positive or negative labels
        Returns:
            A trained model
        """

        if self.classifier_type == 'nb':
            model = NaiveBayesClassifier.train(dataset)
        elif self.classifier_type == 'dt':
            model = DecisionTreeClassifier.train(dataset)
        elif self.classifier_type == 'rf':
            forest = RandomForestClassifier(n_estimators=100, random_state=0)
            model = forest.fit(train_data, train_target)
        elif self.classifier_type == 'nn':
            input_dimension = len(train_data[0])

            model = Sequential()
            model.add(Dense(20, input_dim=input_dimension, activation='relu'))
            model.add(Dropout(0.5))
            model.add(Dense(30, activation='relu'))
            model.add(Dropout(0.5))
            model.add(Dense(20, activation='relu'))
            model.add(Dropout(0.5))
            model.add(Dense(1, activation='sigmoid'))

            print('Compiling model...')
            model.compile(
                optimizer='adam',
                loss='binary_crossentropy',
                metrics=['accuracy'])

            print('Training model...')
            model.fit(
                train_data,
                train_target,
                epochs=50,
                verbose=0,
                class_weight={
                    0: 3,
                    1: 1
                })

            print('Model trained!')

        return model

    def train(self, reviews_filename):
        """ Trains a new naive bayes model or decision tree model

        Args:
            reviews_filename: CSV file of reviews with ratings
        """
        if self.classifier_type == 'nb' or self.classifier_type == 'dt':
            dataset = self.build_dataset(reviews_filename)
            self.model = self.create_trained_model(dataset)
        elif self.classifier_type == 'nn':
            train_data, train_target = self.build_dataset(reviews_filename)
            self.model = self.create_trained_model(
                train_data=train_data, train_target=train_target)
        elif self.classifier_type == 'rf':
            train_data, train_target = self.build_dataset(reviews_filename)
            self.model = self.create_trained_model(
                train_data=train_data, train_target=train_target)

    def evaluate_average_accuracy(self, reviews_filename):
        """ Use stratified k fold to calculate average accuracy of models

        Args:
            reviews_filename: Filename of CSV with reviews to train on
        """

        dataset = []
        train_data = []
        train_target = []
        comments = []
        ratings = []

        if self.classifier_type == 'nb' or self.classifier_type == 'dt':
            dataset = self.build_dataset(reviews_filename)
            comments = [x[0] for x in dataset]
            ratings = [x[1] for x in dataset]
        elif self.classifier_type == 'nn':
            train_data, train_target = self.build_dataset(reviews_filename)
        elif self.classifier_type == 'rf':
            train_data, train_target = self.build_dataset(reviews_filename)

        model_scores = []
        fold = 0

        skfold = StratifiedKFold(n_splits=10, shuffle=True, random_state=None)

        if self.classifier_type == 'nb' or self.classifier_type == 'dt':
            for train, test in skfold.split(comments, ratings):
                fold += 1

                test_data = []
                train_data = []

                for item in test:
                    test_data.append(dataset[item])

                for item in train:
                    train_data.append(dataset[item])

                model = self.create_trained_model(dataset=train_data)

                scores = nltk.classify.util.accuracy(model, test_data)
                model_scores.append(scores * 100)

                if self.classifier_type == 'nb':
                    model.show_most_informative_features()

                print("%.2f%% (+/- %.2f%%)" % (np.mean(model_scores),
                                               np.std(model_scores)))

        elif self.classifier_type == 'nn' or self.classifier_type == 'rf':
            for train, test in skfold.split(train_data, train_target):
                fold += 1

                model = self.create_trained_model(
                    train_data=train_data[train],
                    train_target=train_target[train])

                if self.classifier_type == 'nn':
                    raw_score = model.evaluate(
                        train_data[test], np.array(train_target[test]), verbose=0)
                    print("[err, acc] of fold {} : {}".format(fold, raw_score))
                    model_scores.append(raw_score[1] * 100)

                elif self.classifier_type == 'rf':
                    raw_score = model.score(train_data[test], train_target[test])
                    model_scores.append(raw_score * 100)
                    print("Accuracy of fold " + str(fold) + ": %.2f%% (+/- %.2f%%)" % (
                        np.mean(model_scores), np.std(model_scores)))

        print(f'Average Accuracy: {np.mean(model_scores)}')
        return np.mean(model_scores)

    def save_model(self):
        """ Saves a trained NLTK Model to a Pickle file
        """

        if self.classifier_type == 'nb':
            file_name = 'trained_nb_model.pickle'
        elif self.classifier_type == 'dt':
            file_name = 'trained_dt_model.pickle'

        with open(file_name, 'wb') as pickle_file:
            pickle.dump(
                self.model, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)

        print("Model has been saved!")
    
    def load_model(self, classifier_type ,file_name):
        """ Loads a trained NLTK model from a pickle file
        """

        if classifier_type == 'nb':
            with open(file_name, 'rb') as pickle_file:
                pickle.load(self.model, pickle_file)
            
        elif classifier_type == 'dt':
            with open(file_name, 'rb') as pickle_file:
                pickle.load(self.model, pickle_file)
        
        if self.model is not None:
            print("Model has been loaded!")
