# LLM Development Agent - General Requirements and Best Practices

## Core Principles

### Code Quality Standards
- **Clean Code**: Write readable, maintainable, and self-documenting code
- **SOLID Principles**: Follow Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion principles
- **DRY (Don't Repeat Yourself)**: Eliminate code duplication through proper abstraction
- **KISS (Keep It Simple, Stupid)**: Prefer simple, straightforward solutions over complex ones
- **YAGNI (You Aren't Gonna Need It)**: Don't implement features until they are actually needed

### Design Patterns and Architecture
- **Design Patterns**: Use established patterns (Strategy, Factory, Observer, Chain of Responsibility, etc.) when appropriate
- **Separation of Concerns**: Clearly separate business logic, data access, and presentation layers
- **Dependency Injection**: Use dependency injection to improve testability and maintainability
- **Interface-Based Design**: Program to interfaces, not implementations
- **Modular Architecture**: Create loosely coupled, highly cohesive modules

## Development Standards

### Error Handling and Resilience
- **Graceful Degradation**: Systems should continue to function even when components fail
- **Comprehensive Error Handling**: Anticipate and handle all possible error conditions
- **Meaningful Error Messages**: Provide clear, actionable error messages for users and developers
- **Logging Strategy**: Implement structured logging with appropriate levels (DEBUG, INFO, WARN, ERROR)
- **Fail-Fast Principle**: Detect and report errors as early as possible
- **DO not roll your own**: Do not "roll your own" when well estblished library already exist and should be leveraged
- **DO not duplicate libraries**: Do not use a new library when an existing library has already been implmented within the project.

### Performance and Scalability
- **Optimization**: Write efficient algorithms and data structures
- **Resource Management**: Properly manage memory, file handles, and network connections
- **Batch Processing**: Design for efficient batch operations when handling large datasets
- **Caching Strategy**: Implement appropriate caching mechanisms to improve performance
- **Scalability Considerations**: Design systems that can handle increased load

### Security Best Practices
- **Input Validation**: Validate and sanitize all user inputs
- **Data Protection**: Secure sensitive data both in transit and at rest
- **Principle of Least Privilege**: Grant minimum necessary permissions
- **Secure Defaults**: Use secure configurations by default
- **Audit Trail**: Maintain logs of security-relevant events

## Testing Requirements

### Test-Driven Development
- **Unit Testing**: Write comprehensive unit tests with high coverage (>80%)
    - integration and user input/scenarios mocking permitted
    - Goal: validate business logic
- **Integration Testing**: Test component interactions and system workflows
    - user input and scenarios mocking permitted
    - Goal: verify component interoperability
- **End-to-End Testing**: Validate complete user scenarios
    - user UI mocking permitted
    - Goal: verify workflows without ui/us layer
- **Journey Testing**: Validate complete user ui/ux scenarios
    - simulated user response permitted
    - Goal: User UI experience funcitonal
    - When testing a journey test file, **EXIT 0 with NO OUTPUT is a sign that the ui hung and expected user interaction** Requiring user input is not permitted for Journey testing. User input must be automated.
- **Test Automation**: Automate test execution and reporting
- **Test Data Management**: Use appropriate test data and mock objects. Minimized MOCKING as much as possible

**When running test suites**
- Run from most fundamental to most complex. 
- Do not run a test or test file that is dependent on implementations that have not been tested.

### Quality Assurance
- **Code Reviews**: Implement peer review processes
- **Static Analysis**: Use linting tools and static code analyzers
- **Continuous Integration**: Automate build, test, and deployment processes
- **Performance Testing**: Validate system performance under expected loads
- **Security Testing**: Include security validation in testing processes

## Documentation Standards

### Code Documentation
- **Self-Documenting Code**: Write code that explains itself through clear naming and structure
- **Inline Comments**: Add comments for complex logic and business rules
- **API Documentation**: Document all public interfaces and their usage
- **Architecture Documentation**: Maintain high-level system architecture diagrams
- **Change Documentation**: Document significant changes and their rationale

### User Documentation
- **Installation Guides**: Provide clear setup and installation instructions
- **User Manuals**: Create comprehensive user guides with examples
- **Troubleshooting Guides**: Document common issues and their solutions
- **FAQ**: Maintain frequently asked questions and answers
- **Version Documentation**: Document changes between versions

## Data Management

### Data Integrity
- **Validation**: Implement comprehensive data validation at all entry points
- **Consistency**: Ensure data consistency across all system components
- **Backup Strategy**: Implement regular data backup and recovery procedures
- **Data Migration**: Plan for safe data migration and schema changes
- **Audit Trails**: Maintain records of data changes and access

### Privacy and Compliance
- **Data Minimization**: Collect and store only necessary data
- **Retention Policies**: Implement appropriate data retention and deletion policies
- **Access Controls**: Restrict data access based on user roles and permissions
- **Compliance**: Adhere to relevant data protection regulations (GDPR, CCPA, etc.)
- **Anonymization**: Use data anonymization techniques when appropriate

## User Experience

### Interface Design
- **Usability**: Design intuitive, user-friendly interfaces
- **Accessibility**: Ensure applications are accessible to users with disabilities
- **Responsive Design**: Create interfaces that work across different devices and screen sizes
- **Performance**: Optimize interface responsiveness and loading times
- **Consistency**: Maintain consistent design patterns and interactions

### User Feedback
- **Progress Indicators**: Provide clear feedback on long-running operations
- **Error Recovery**: Help users recover from errors with clear guidance
- **Help Systems**: Integrate contextual help and documentation
- **User Testing**: Conduct usability testing with real users
- **Feedback Mechanisms**: Provide ways for users to report issues and suggestions

## Deployment and Operations

### DevOps Practices
- **Infrastructure as Code**: Manage infrastructure through version-controlled code
- **Continuous Deployment**: Automate deployment processes with proper safeguards
- **Monitoring**: Implement comprehensive system monitoring and alerting
- **Configuration Management**: Externalize configuration and manage environments
- **Rollback Procedures**: Plan for quick rollback in case of deployment issues

### Maintenance and Support
- **Version Control**: Use proper version control with meaningful commit messages
- **Release Management**: Plan and execute controlled releases
- **Issue Tracking**: Maintain systematic issue tracking and resolution
- **Performance Monitoring**: Continuously monitor system performance and health
- **Capacity Planning**: Plan for future growth and resource needs

## Communication and Collaboration

### Team Collaboration
- **Code Standards**: Establish and enforce team coding standards
- **Knowledge Sharing**: Facilitate knowledge transfer and documentation
- **Code Reviews**: Implement constructive peer review processes
- **Pair Programming**: Use collaborative programming techniques when appropriate
- **Regular Communication**: Maintain regular team communication and updates

### Stakeholder Management
- **Requirements Gathering**: Systematically gather and document requirements
- **Progress Reporting**: Provide regular, transparent progress updates
- **Change Management**: Manage scope changes through proper processes
- **User Involvement**: Include users in design and testing processes
- **Expectation Management**: Set and manage realistic expectations

## Continuous Improvement

### Learning and Adaptation
- **Technology Evaluation**: Regularly evaluate new technologies and approaches
- **Best Practice Updates**: Stay current with industry best practices
- **Retrospectives**: Conduct regular project retrospectives and lessons learned
- **Skill Development**: Continuously improve technical and soft skills
- **Innovation**: Encourage experimentation and innovation within appropriate bounds

### Process Optimization
- **Workflow Analysis**: Regularly analyze and optimize development workflows
- **Tool Evaluation**: Assess and adopt tools that improve productivity
- **Automation**: Automate repetitive tasks and processes
- **Metrics Collection**: Collect and analyze development and system metrics
- **Feedback Integration**: Incorporate feedback into process improvements

## Environment and Configuration Management

### Environment Constraints
- **Environment Files**: Never modify environment files without explicit permission
- **Configuration Security**: Protect sensitive configuration data
- **Environment Parity**: Maintain consistency across development, testing, and production environments
- **Dependency Management**: Carefully manage external dependencies and versions
- **Isolation**: Use appropriate isolation techniques (containers, virtual environments, etc.)

### Change Control
- **Permission-Based Changes**: Require explicit permission for sensitive changes
- **Change Documentation**: Document all significant configuration changes
- **Rollback Plans**: Maintain ability to rollback configuration changes
- **Testing**: Test configuration changes in non-production environments first
- **Approval Processes**: Implement appropriate approval processes for critical changes

### Context Awareness
- **roo.md** if a file is in a directory and that directory also has a roo.md file in it, the roo.md file contains important context specific to that directory and should be read prior to interacting with files in the directory