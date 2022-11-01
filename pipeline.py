import datetime

import dill
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline




def main():
    df = pd.DataFrame.from_dict({"street": ['street1', 'str2'],
                                 "app": [1, 2],
                                 "house": [55, 20],
                                 "square": [55, 45],
                                 'param': [25, 33],
                                 "y": [10000, 5000]})
    ridge_regression = Ridge(alpha=0.1)

    pipe = Pipeline(steps=[('model', ridge_regression)])
    pipe.fit(df[['square', 'param']], df.y)
    with open('pipe.pkl', 'wb') as file:
        dill.dump({
            'model': pipe,
            'metadata': {
                'name': '_____',
                'author': 'NSKTeam',
                'version': 1.0,
                'date': datetime.datetime.now(),
                'type': type(pipe.named_steps['model']).__name__
            }
        }, file)
    df1 = pd.DataFrame.from_dict({"street": ['str2'],
                                  "app": [2],
                                  "house": [24],
                                  "square": [58],
                                  'param': [26]})
    print(pipe.predict(df1[['square', 'param']]))


if __name__ == '__main__':
    main()