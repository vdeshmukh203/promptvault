# promptvault

Versioned prompt template storage with history tracking.

```python
from promptvault import Promptvault

vault = Promptvault()
vault.save("greeting", "Hello, {name}!")
vault.save("greeting", "Hi there, {name}! How are you?")
print(vault.get("greeting"))  # latest version
print(vault.history("greeting"))  # all versions
```
