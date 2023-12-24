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
from evaluate import fpl_evaluate
from sklearn import linear_model, tree
import matplotlib.pyplot as plt

target_season = '2023-24'
target_gameweek = 15
fplapi = fplapi_data(target_season)
vastaav = vastaav_data('../Fantasy-Premier-League/data', target_season)
eval = fpl_evaluate()

def main():
    print('Extracting data & reducing feature set...')
    week_data = vastaav.get_training_data(target_gameweek - 1)

    # Lets train a model
    print('Training model...')
    gk_model = linear_model.LinearRegression()
    gk_model.fit(week_data[0][0], week_data[0][1])

    def_model = linear_model.LinearRegression()
    def_model.fit(week_data[1][0], week_data[1][1])

    mid_model = linear_model.LinearRegression()
    mid_model.fit(week_data[2][0], week_data[2][1])

    fwd_model = linear_model.LinearRegression()
    fwd_model.fit(week_data[3][0], week_data[3][1])

    print('Models trained!')

    for i in range(target_gameweek, target_gameweek + 3):
        week_data = vastaav.get_training_data(i)

        # Predict points for GWi
        print(f'Predicting points for GW{i}...')
        gk_predictions = gk_model.predict(week_data[0][0])
        def_predictions = def_model.predict(week_data[1][0])
        mid_predictions = mid_model.predict(week_data[2][0])
        fwd_predictions = fwd_model.predict(week_data[3][0])

        eval.score_model(gk_predictions, week_data[0][1])
        eval.score_model(def_predictions, week_data[1][1])
        eval.score_model(mid_predictions, week_data[2][1])
        eval.score_model(fwd_predictions, week_data[3][1])

        # Plot predictions vs actual points for GWi
        # Colour code by position
        plt.title(f'GW{i} predictions vs actual points')
        plt.xlabel('Predicted points')
        plt.ylabel('Actual points')
        plt.scatter(gk_predictions, week_data[0][1], color='red')
        plt.scatter(def_predictions, week_data[1][1], color='blue')
        plt.scatter(mid_predictions, week_data[2][1], color='green')
        plt.scatter(fwd_predictions, week_data[3][1], color='orange')
        plt.legend(['GK', 'DEF', 'MID', 'FWD'])
        # Plot y=x line to show perfect prediction
        plt.plot([0, 20], [0, 20], color='black')

        plt.show()






if __name__ == "__main__":
    main()