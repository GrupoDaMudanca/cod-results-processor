# CoD Result Processor

The `CoD Result Processor` is a tool designed to process and analyze results from Call of Duty clan games, generating CSV files based on the results. This project automates the process of reading the data and organizing it in a structured format.

## Features

- **Result Processing:** Extracts and processes game results from Call of Duty clan matches.
- **CSV Generation:** Outputs the processed data into CSV files for easy storage and analysis.
- **Dockerized Environment:** Simplified deployment and running via Docker.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)

## Setup

- Build the Docker image:

    ```bash
    make build
    ```

- To build without using the cache:

    ```bash
    make build-no-cache
    ```
## Processing Game Results

To process the Call of Duty game results and generate the CSV output, run the following command:

```bash
make process-results
```

## Opening a Shell in the Container

If you need to debug or manually interact with the environment, you can open a bash shell inside the Docker container:
    
```bash
make shell
```
