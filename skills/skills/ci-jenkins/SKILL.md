---
name: ci-jenkins
description: >-
  Jenkinsfile pipeline syntax, stages, agents, shared libraries.
  Use this skill when working with Jenkins CI/CD pipelines.
---

# Jenkins CI/CD

## Declarative Pipeline

```groovy
pipeline {
    agent any

    environment {
        APP_NAME = 'my-service'
        REGISTRY = 'gcr.io/my-project'
    }

    stages {
        stage('Build') {
            steps {
                sh './gradlew clean build -x test'
            }
        }
        stage('Test') {
            steps {
                sh './gradlew test'
            }
            post {
                always {
                    junit 'build/test-results/**/*.xml'
                }
            }
        }
        stage('Docker') {
            when { branch 'main' }
            steps {
                sh "docker build -t ${REGISTRY}/${APP_NAME}:${BUILD_NUMBER} ."
                sh "docker push ${REGISTRY}/${APP_NAME}:${BUILD_NUMBER}"
            }
        }
        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh "kubectl set image deployment/${APP_NAME} ${APP_NAME}=${REGISTRY}/${APP_NAME}:${BUILD_NUMBER}"
            }
        }
    }

    post {
        failure {
            slackSend channel: '#builds', message: "FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
    }
}
```

## Key Concepts

- **`agent`**: Where to run (any, docker, label)
- **`stages`/`stage`**: Named pipeline phases
- **`steps`**: Commands within a stage
- **`when`**: Conditional execution (`branch`, `expression`, `environment`)
- **`post`**: After-stage/after-pipeline actions (`always`, `success`, `failure`)
- **`environment`**: Pipeline-level or stage-level env vars
- **`credentials()`**: Inject secrets from Jenkins credential store

## Guidelines

- Use declarative syntax over scripted when possible
- Store `Jenkinsfile` in the repo root
- Use `when` blocks to skip stages (don't use if/else in steps)
- Use shared libraries for reusable pipeline logic
- Archive artifacts and test results with `post` blocks
- Use `credentials()` binding — never hardcode secrets
