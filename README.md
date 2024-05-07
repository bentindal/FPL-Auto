# Automating FPL Through the Use of Machine Learning and Strategy

## Please Note this is a Work In Progress! Due to be Completed in May

Created by Benjamin Tindal as part of my dissertation project "Transforming Fantasy Football Management
with Data-Driven Machine Learning" at the University of Sheffield.

## Introduction

This project is a fully autonomous Fantasy Premier League (FPL) team selection system. It explores the use of machine learning techniques to predict the performance of players in the English Premier League and uses these predictions to select a team of players that will score the most points in the upcoming weeks.

The project is split into multiple parts, each of which is described in detail below.

## Dataset

Special thanks to Vastaav Anand for his FPL Data Scraper [1], which was used to collect the historical data for this project. The project can be found <a href="https://github.com/vaastav/Fantasy-Premier-League">here</a>.

## Machine Learning

The machine learning makes use of a Gradient Boosting tree regression model from the sklearn library [2], which is trained on the historical data collected from the FPL API. The model is trained to predict the points scored by each player in the upcoming week and is then used to select the team of players that will score the most points.

## Team Selection

The project fully aims to abide by the rules of the FPL game, so the team selection process, chip usage, transfers, captaincy and substituions are all fully automated.

## Running the Project

The evaluate.py, team.py, and data.py classes are self-contained in the fpl auto folder. You can
import these functions using the fpl auto prefix. The manager.py & model.py provide complete
examples of how to use the code

## Keeping the Dataset up to date

I will not be regularly maintaining the dataset. If you want to update it, you must do so manually. I
recommend cloning <a href="https://github.com/vaastav/Fantasy-Premier-League">Vaastav’s repository</a> [1]
and running his global scraper.py file, copying the generated data directory over to this project,
and then run model.py with the appropriate arguments for the season to generate predictive model’s
for any additional weeks.

## Bibliography

[1] FPL Historical Dataset, Anand, V., 2019. https://github.com/vaastav/Fantasy-Premier-League/

[2] Scikit-learn: Machine Learning in Python, Pedregosa et al., JMLR 12, pp. 2825-2830, 2011. https://scikit-learn.org/stable/
