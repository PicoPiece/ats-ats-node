// Build and push ats-node-test Docker image (GHCR).
// Triggered by: poll SCM on this repo, or manual run.
// Requires: node with Docker (and ideally buildx), GHCR_CREDENTIALS_ID in Jenkins.
pipeline {
    agent { label 'fw-build' }

    parameters {
        string(
            name: 'IMAGE',
            defaultValue: 'ghcr.io/picopiece/ats-node-test:latest',
            description: 'Full image name (registry/owner/name:tag)'
        )
        string(
            name: 'GHCR_CREDENTIALS_ID',
            defaultValue: '',
            description: 'Jenkins credentials ID for GHCR (username+password or token). Required for push.'
        )
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker login') {
            when { expression { return params.GHCR_CREDENTIALS_ID?.trim() } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: params.GHCR_CREDENTIALS_ID,
                    usernameVariable: 'REG_USER',
                    passwordVariable: 'REG_PASS'
                )]) {
                    sh 'echo "$REG_PASS" | docker login ghcr.io -u "$REG_USER" --password-stdin'
                }
            }
        }

        stage('Build and push image') {
            steps {
                dir('docker/ats-node-test') {
                    script {
                        def hasBuildx = sh(script: 'docker buildx version >/dev/null 2>&1', returnStatus: true) == 0
                        def fullImage = params.IMAGE.trim().toLowerCase()
                        def doPush = params.GHCR_CREDENTIALS_ID?.trim()

                        if (hasBuildx && doPush) {
                            sh """
                                docker buildx create --name ats-builder --use 2>/dev/null || docker buildx use ats-builder
                                docker buildx build --platform linux/amd64,linux/arm64 --tag ${fullImage} --push .
                            """
                        } else if (hasBuildx && !doPush) {
                            sh "docker build --pull -t ${fullImage} ."
                            echo "⚠️ GHCR_CREDENTIALS_ID not set — image built locally only (no push)"
                        } else {
                            sh "docker build --pull -t ${fullImage} ."
                            if (doPush) {
                                sh "docker push ${fullImage}"
                            } else {
                                echo "⚠️ GHCR_CREDENTIALS_ID not set — image built locally only (no push)"
                            }
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            echo "✅ Image built and pushed: ${params.IMAGE}"
        }
        failure {
            echo "❌ Build or push failed. Check GHCR_CREDENTIALS_ID and node Docker/buildx."
        }
    }
}
