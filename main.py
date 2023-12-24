'''
FPL Automation Project
Author: Benjamin Tindal
'''

import numpy as np
import pandas as pd
import requests, json
from pprint import pprint
import json
from fplapi import fplapi_data
from vastaav import vastaav_data
from sklearn import linear_model, tree
import matplotlib.pyplot as plt

target_season = '2023-24'
target_gameweek = 4
fplapi = fplapi_data(target_season)
vastaav = vastaav_data('../Fantasy-Premier-League/data', target_season)

def main():
    print('Extracting data & reducing feature set...')
    week_one = vastaav.get_training_data(target_gameweek - 1)

    # Get features and labels for FWD
    features = week_one[3][0]
    labels = week_one[3][1]

    # Lets train a model
    print('Training model...')
    model = linear_model.LinearRegression()
    model.fit(features, labels)
    print('Model trained!')

    for i in range(target_gameweek, target_gameweek + 10):
        # Get features for GWi
        week_data = vastaav.get_training_data(i)
        features = week_data[3][0]
        labels = week_data[3][1]

        # Predict points for GWi
        print(f'Predicting points for GW{i}...')
        predictions = model.predict(features)
        
        # Calculate error
        error = 0
        square_error = 0
        accuracy = 0
        for i in range(len(predictions)):
            error += abs(predictions[i] - labels[i])
            square_error += (predictions[i] - labels[i]) ** 2
            if predictions[i] == labels[i]:
                accuracy += 1
        error /= len(predictions)
        square_error /= len(predictions)
        accuracy /= len(predictions)

        print(f'Average error: {error}')
        print(f'Average square error: {square_error}')
        print(f'Accuracy: {accuracy}')

        # Plot predictions vs actual points
        plt.scatter(predictions, labels)
        plt.xlabel('Predicted points')
        plt.ylabel('Actual points')
        # Plot y=x
        x = np.linspace(0, 20, 100)
        plt.plot(x, x, '-r', label='y=x')

        plt.show()






if __name__ == "__main__":
    main()