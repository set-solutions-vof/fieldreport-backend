class InviteAlreadyExists(Exception):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Invite already exists: {email}")
