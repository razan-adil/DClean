# Data ingestion: The data Departement asked AI depart (me) to create a model that cleans a dataset to make it ready to be integrated.

## Objective:
To insert an csv or excel file and output a file that has the data cleaned. The goal shall be making a system pipline to clear the data and form a batch of files. While still make it generalized and not only applied to a single case.

## Problem: 
Since the AI is stochastic and data cleaning should be deterministic applying a model on the spot is not suffcient where most of the data should be perserved and we can't usually tolerate a percentage of data corruption especially on Identity Data.
(We could apply the model in the deduplicates problems like the Splink unsupervised model).

## Data groups#:
1. Identity: This data is the data where it has the identification info about the user: Name, Email, Phone (+966).
2. Structed/MetaData: This data is a data where it doesnt identficate the person but tells additional info about him: Major, University.
3. Catagorical/MultiSelcet: This data is usually a multi select data such as: Skills, agreement.
4. Free-Form: This data is the free form space where it takes from the user an input of a question like: Why do you want to join.

Making a well grouping schema would help acheive a greater result in making the Pipline genrelized and be applied for different files and datasets.

## Where to use AI:
We apparentally can't use AI on the data cleaning proccess but we can use it in the grouping phase and where a model will label the data under the wanted groups. 

### examples:
- Before going into cleaning proccess we apply labling model to label each column to group of the 4 groups.
- To detect duplicates across files and merge them into single entry to ensure no users with the multiple UUID.
- To detect duplicates of a single file and make sure duplicates gets eliminated.
also there are more ways.
