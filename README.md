# FPL Automation Dissertation Project

By Benjamin Tindal, completed as part as my dissertation at the University of Sheffield.

## Introduction

This project is a fully autonomous Fantasy Premier League (FPL) team selection system. It explores the use of machine learning techniques to predict the performance of players in the English Premier League, and uses these predictions to select a team of players that will score the most points in the upcoming gameweek.

The project is split into multiple parts, each of which is described in detail below.

## Data Collection

Special thanks to Vastaav Anand for his FPL API, which was used to collect the historical data for this project. The API can be found <a href="https://github.com/vaastav/Fantasy-Premier-League">here</a>.

The data collection process is split into two parts: historical data collection and live data collection, where the former is used to train the machine learning models and the latter is used to make predictions for the upcoming gameweek.

## Machine Learning

The machine learning makes use of a Gradient Boosting regression model, which is trained on the historical data collected from the FPL API. The model is trained to predict the points scored by each player in the upcoming gameweek, and is then used to select the team of players that will score the most points.

## Team Selection

The project fully aims to abide by the rules of the FPL game, and so the team selection process is split into two parts: the initial team selection and the transfer selection.

* Work in Progress! *

TODO - Initial Team Selection
TODO - Transfer Selection
