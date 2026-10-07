# This model shall accept all type of dataset which we can call an ETL model (Extract, Tranform, Load). Here are a set of rules:

## A. The input is a CSV/Excel and the output is CSV/Excel:
This pipeline shall accept a structed data file format and output also the same.

## B. The Column grouping:
There should be a small suffecient LLM Model to be ran locall that can reasonably group the colomuns to 4 groups as meantioned in the Schema. This step is crucial for Generalization hence the model should be applicable on few columns datasets and many columns datasets.

## C. The contractor:
This is the part of the model where we also could use an LLM to map the current column with the corresponding name in the code using a YAML file. The problem here is the code is determinstic but the names of the columns are stochastic and varying we need to search for a concluded soution for this part.

## D. Cleaning Proccess:

### 1. Normalized Identity:
The IDs should only be normalized and not be intercated with an AI model because they are Deterministic and shall be accurate. Names could be analyzed by an NLP both ARABIC and ENGLISH.
The emails should be lowercased and also the domain should be currect (We need to check the email using some callled tools). Finally the Phone numbers shoud be in the format of Saudi Arabia and should be written with the SA Phone prefix.

### 2. MetaData:
The MetaData is the data that is informative and yet additonal to the ID. For this type we also need to use some LLM to normalize the text especially the universtiy. Some could write UJ insted of Universty of Jeddah, this should also be normalized and handled while there is no affirmative way to write it we shall use LLM to ensure the data is normalized and this data could be handled even when it is inaccurate. Also the timestamp should be handeled and be in a good readable format for both machine and humans if possible, if not priortrize machine.

### 3. MultiSelect + Free form:
For the Multi select usually you would see the values to be in the same column in a certain normalized format -Because they choose of existanced values-. However, these two last types are not too different. We can Keep the multiselect as is but the free form we can enter the String the user typed (Does not need normalization) and make sure it doesnt have any malicus injection.

### 4. Deduplication:
For this part and for now we will use the https://moj-analytical-services.github.io/splink/ to find duplication in the same file and ensure resultion of it. We can use the time to ensure the last submitted data is the clean one but there could be some problems where people could send mistake send. But the overall assumption is the last one is probably the correct one.

## E. The code and implementaion:
The Pipeline should be work on different computers where it should have the following:
- The code should not have a single path it should be installed in a directory and unpack in that directory. (Ofcourse this would be after approval since testing should be local for faster env)
- Maintainable, the code should be able to have room for scalability and fixing. TDD is somehting encourged during this project.
- Doucmented, If you are going to add lines you should write it in a doucmentaion.
- Do not overenginner