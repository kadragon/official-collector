from openai import OpenAI
from pydantic import BaseModel

class ClassficationType(BaseModel):
    classification: str
    viewing: str
    ReasonForClassification: str
    


class AIManager:
    def __init__(self):
        self.client = OpenAI()

    def get_embedding(self, title):
        response = self.client.embeddings.create(
            input=title,
            model="text-embedding-3-small"
        )

        return response.data[0].embedding
    
    def find_match(self, title, vector_info):
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
### Prompt
You are an intelligent assistant specializing in categorizing official documents based on vector similarity metadata and assigning their handling attributes. Your primary objectives are to:

1. Identify the closest match for a given document title using the `score` in the vector similarity data.
2. Assign `classification` and `viewing` attributes based on the closest match while adhering to predefined constraints.
3. Provide a clear explanation for the classification decision in Korean, termed as `ReasonForClassification`.

#### Allowed Values
- `classification`:
```
["팀장님_전결", "원장님_결재", "담당_윤인자", "담당_이종선", "담당_홍성민", "담당_황미연", "담당_우미인", "담당_김수현", "담당_이상수"]
```

- `viewing`:
```
["원장님-", "원장님+", "공람없음", "일반직", "조교", "팀장님", "원장님만"]
```

{'matches': [
    {'id': '<unique_id>',
     'metadata': {'classification': '<classification>',
                  'title': '<title>',
                  'viewing': '<viewing>'},
     'score': <score>},
     ...
]}
```

### Instructions:
1. For each document title:
   - Evaluate all `matches` to identify the most relevant entry by prioritizing the highest `score`.
   - In cases of ties, assess metadata holistically, factoring in both `classification` and `viewing` attributes for contextual relevance.
   - Utilize the vector similarity metadata beyond the score to ensure logical consistency in selection.

2. Populate the following output fields:
   - `classification`: Derived from the matched entry's metadata.
   - `viewing`: Derived from the matched entry's metadata.
   - `ReasonForClassification`: A brief explanation for the `classification` choice, written in Korean.

3. Adhere strictly to the predefined `classification` and `viewing` lists to prevent invalid assignments.

4. Document ambiguous cases and clarify decisions using logical reasoning tied to both vector similarity and metadata analysis.

### Additional Notes
- The decision process must balance both `score` and metadata elements, with a preference for the highest-scoring entry unless contextual factors dictate otherwise.
- Ensure that explanations in `ReasonForClassification` are concise yet meaningful, reflecting the rationale transparently.
                 """},
                {"role": "user", "content": f'title: {title}\n\nRetrieve info: {vector_info}'}
            ],
            response_format=ClassficationType
        )
        
        return completion.choices[0].message.parsed
        
