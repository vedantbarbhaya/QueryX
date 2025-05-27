# Contributing to QueryX

Thank you for your interest in contributing to QueryX! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/QueryX.git
   cd QueryX
   ```
3. **Set up the development environment** following the README.md instructions
4. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Guidelines

### Code Style

#### Python (Backend)
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Use meaningful variable and function names
- Keep functions small and focused

#### TypeScript/React (Frontend)
- Use TypeScript for all new code
- Follow React best practices (hooks, functional components)
- Use Chakra UI components consistently
- Write self-documenting code with clear component interfaces

### Code Organization

#### Backend Structure
```
backend/app/
├── api/          # FastAPI route handlers
├── core/         # Business logic and utilities
├── rag/          # RAG system components
├── crawler/      # Document processing
└── tests/        # Test files
```

#### Frontend Structure
```
frontend/
├── app/          # Next.js App Router pages
├── src/
│   ├── components/  # Reusable React components
│   ├── types/       # TypeScript definitions
│   └── utils/       # Utility functions
└── public/       # Static assets
```

### Testing

#### Backend Tests
- Write unit tests for all business logic
- Use pytest for testing framework
- Aim for >80% code coverage
- Include integration tests for API endpoints

```bash
cd backend
python -m pytest app/tests/ -v --cov=app
```

#### Frontend Tests
- Write unit tests for utility functions
- Include component tests for complex components
- Use Jest and React Testing Library

```bash
cd frontend
npm test
```

### Git Workflow

1. **Keep commits atomic** - one logical change per commit
2. **Write descriptive commit messages**:
   ```
   feat: add user authentication system
   
   - Implement JWT-based authentication
   - Add login/logout endpoints
   - Create user registration flow
   ```
3. **Rebase before pushing** to maintain clean history
4. **Squash commits** if you have multiple commits for a single feature

### Commit Message Format

Use conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### Pull Request Process

1. **Update documentation** if your changes affect the API or user interface
2. **Ensure all tests pass** locally before submitting
3. **Include a clear description** of what your PR does and why
4. **Reference any related issues** using GitHub keywords (e.g., "Fixes #123")
5. **Request review** from maintainers

### Pull Request Template

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots for UI changes.

## Related Issues
Closes #issue_number
```

## Code Quality Standards

### Performance
- Avoid N+1 queries in database operations
- Use appropriate indexing for database queries
- Implement caching for expensive operations
- Optimize frontend bundle size

### Security
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Don't commit secrets or API keys

### Accessibility
- Use semantic HTML elements
- Provide proper ARIA labels
- Ensure keyboard navigation works
- Test with screen readers

## Development Environment

### Required Tools
- Python 3.11+
- Node.js 18+
- Docker (for RabbitMQ and Redis)
- Git

### IDE Setup
Recommended extensions for VS Code:
- Python
- Pylance
- TypeScript and JavaScript Language Features
- ES7+ React/Redux/React-Native snippets
- Prettier
- ESLint

### Environment Variables
Copy `env.example` to `.env` and configure:
- OpenAI API key
- Database URLs
- Secret keys

## Reporting Issues

### Bug Reports
Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python/Node versions)
- Error messages and stack traces

### Feature Requests
Include:
- Clear description of the feature
- Use cases and benefits
- Potential implementation approach
- Any related issues or discussions

## Questions and Support

- **GitHub Discussions** - For general questions and discussions
- **GitHub Issues** - For bug reports and feature requests
- **Discord** - For real-time chat (if applicable)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to QueryX! 🚀 