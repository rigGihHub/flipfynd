# FlipFynd v0.14.19

- Seller search now keeps its sidebar panel open after a checkpointed three-page batch.
- The partial state is labelled as a deliberate batch stop instead of looking frozen or complete.
- The UI states the saved listing count, next page and that **Fortsätt söka** resumes without starting over.
- Search batching remains bounded to avoid Streamlit and Tradera timeouts.
