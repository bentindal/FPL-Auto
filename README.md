# Automating FPL Through the Use of Machine Learning and Strategy
## Please Note this is a Work In Progress! Due to be Completed in May
Created by Benjamin Tindal as part of my dissertation "Unleashing Strategy through the Use of Machine Learning in Fantasy Football Automation" at the University of Sheffield.

## Introduction

This project is a fully autonomous Fantasy Premier League (FPL) team selection system. It explores the use of machine learning techniques to predict the performance of players in the English Premier League and uses these predictions to select a team of players that will score the most points in the upcoming weeks.

The project is split into multiple parts, each of which is described in detail below.

## Data Collection

Special thanks to Vastaav Anand for his FPL API [1], which was used to collect the historical data for this project. The API can be found <a href="https://github.com/vaastav/Fantasy-Premier-League">here</a>.

The data collection process is split into two parts: historical data collection and live data collection, where the former is used to train the machine learning models and the latter is used to make predictions for the upcoming gameweek.

## Machine Learning

The machine learning makes use of a Gradient Boosting tree regression model from the sklearn library [2], which is trained on the historical data collected from the FPL API. The model is trained to predict the points scored by each player in the upcoming week and is then used to select the team of players that will score the most points.

## Team Selection

The project fully aims to abide by the rules of the FPL game, so the team selection process is split into two parts: the initial and transfer selection.

* Work in Progress! *

TODO - Initial Team Selection

TODO - Transfer Selection

## Bibliography
[1] FPL Historical Dataset, Anand, V., 2019. https://github.com/vaastav/Fantasy-Premier-League/

[2] Scikit-learn: Machine Learning in Python, Pedregosa et al., JMLR 12, pp. 2825-2830, 2011. https://scikit-learn.org/stable/
