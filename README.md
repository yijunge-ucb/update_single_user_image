## Update_single_user_image 

The script takes an environment.yml as the input and prints an updated_environment.yml, with updated conda dependencies and pip dependencies. 

The conda dependencies versions are pulled from anaconda.org/conda-forge and the pip versions are pulled from pypi.org, by parsing the html response. 


To run the script, 

```python3
python3 update_single_user_image.py
```

## Example Output for data100: 
See environment.yml(input) and updated_environment.yml (output)
