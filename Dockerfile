FROM python:3.12-slim

# set a directory for the app
WORKDIR /app

# copy the requirements.txt file to the app directory
COPY requirements.txt .

# install the dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the app to the app directory
COPY . .

# run the app
CMD ["python", "main.py"]