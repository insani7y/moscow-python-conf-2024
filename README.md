<!-- omit in toc -->

# PYpelines

<img src="./logo.png" width="200px"><br>
This is python-based fullstack CI/CD pipelines made for and by python community users.

Not groundbreaking, but very nice features:

- full coverage of the best practices of not only our community, but of the world at large: linters that won't miss most bugs
- presets for those who don't want to configure anything
- flexible docker support: pipelines are compatible with any docker-based project
- first class frontend support (for fullstack developers)
- trivy security scanner
- linters for docker files and for k8s manifests
- badge with the number of lines of code ![](https://img.shields.io/static/v1?label=lines%20of%20code&message=100&color=brightgreen)
- badge with the versions of your service on the `preview` and `production` environments: you will always see where the release is! ![](https://img.shields.io/static/v1?label=preview%20version&message=2.3.1&color=blue) ![](https://img.shields.io/static/v1?label=production%20version&message=2.4.0&color=green)

Contents:

- [Requirements](#requirements)
- [Stages](#stages)
- [Project versioning and images tagging](#project-versioning-and-images-tagging)
- [Quickstart examples](#quickstart-examples)
  - [Recommended usage](#recommended-usage)
  - [Usage of whole preset](#usage-of-whole-preset)
  - [Usage some parts of preset](#usage-some-parts-of-preset)
  - [Creating complex tests](#creating-complex-tests)
  - [Gitlab Integrations](#gitlab-integrations)
  - [Used utilities](#used-utilities)
- [Environment variables](#environment-variables)
  - [Skiping some parts of pipeline](#skiping-some-parts-of-pipeline)
- [Advanced](#advanced)
  - [Rules](#rules)
  - [Frontend package managers](#frontend-package-managers)
  - [Type coverage support](#type-coverage-support)
  - [Advanced stages](#advanced-stages)
  - [static-analyze](#static-analyze)
  - [build](#build)
  - [test](#test)
  - [appsec](#appsec)
  - [scan](#scan)
  - [publish](#publish)
  - [image-release](#image-release)
  - [deploy](#deploy)
  - [gitlab-release](#gitlab-release)
  - [e2e](#e2e)
- [Badges](#badges)
- [FAQ](#faq)

## Requirements

- [Trunk-based development](https://trunkbaseddevelopment.com/)
- Python-based project, frontend-based project (basically we contain frontend pipelines only for those who wish for fullstack development)
- Semver versioning via git tags
- Project structure:
  - Folder `chart` in the root of your project, where helm chart is presented (it can be renamed with `DEPLOY_HELM_CHART` variable)
- [Some necessary environment variables](#environment-variables)

## Stages

Any available preset contains a subset of all stages, available in the pipeline. More accurately, the following:
| Stage | Description |
|---|---|
| `static-analyze` | Responsible for linting your code/Dockerfiles/Manifests |
| `build` | Used to build multiarch images via Dockerfile |
| `test` | Tests your builded image in `docker-compose` or right in cli |
| `appsec` | Application security scan |
| `scan` | Scan your image with sonar |
| `publish` | Publish project to Artifactory pypi |
| `image-release` | Release image with tag |
| `deploy` | Deploy to dev/prev/prod |
| `gitlab-release` | Create a gitlab release and set release-badge |
| `e2e` | Run e2e tests |

# Project versioning and images tagging

The tags automatically applied to images for their publication in Artifactory are determined through various stages and jobs.

`Version from Git Tag`: When a Git tagging event occurs, the corresponding version tag is used. This version tag (CI_COMMIT_TAG) is directly utilized for versioning the image, allowing a clear correlation of built images with code versions in the repository.

`Short SHA of Commit`: In addition to the version tag, an image can be tagged with the short hash of the commit (CI_COMMIT_SHORT_SHA), providing uniqueness and the ability to trace the image back to a specific change in the code.

`Environment Tag`: Depending on the environment to which deployment is being made (e.g., dev, test, preview, prod), an image can receive a corresponding environment tag, simplifying the identification of the image by purpose and used environment.

`'Scanned' Tag`: After successfully passing vulnerability scanning, an image is assigned the scanned tag, indicating that the image has been checked and deemed safe for use.

`'Tested' Tag`: Similarly, an image can receive a tested tag if it has successfully passed all tests. This is an additional confirmation of the image's quality and readiness for deployment.

All these tags are applied in accordance with the logic of the CI/CD pipeline tasks and are used for version management, tracking, and quality control of images that are then published in Artifactory. This approach ensures precise versioning, security, and traceability of images in the continuous integration and delivery process.

## Quickstart examples

### Recommended usage

The use of standardized pipelines is adapted for application through presets. It's recommended to use the whole preset. However, if for some reason you do not want to use the entire pipeline, you are free to assemble your own pipeline from individual primitives.

### Usage of whole preset

1. You need to set all [environment variables](#environment-variables)
1. Include preset inside .gitlab-ci.yml file.

```yaml
# .gitlab-ci.yml
variables:
  ENABLE_ISOLATION: "true"

include:
  - project: "python-community/pypelines"
    file: "presets/backend--v1.yml"
```

By default, we don't run tests in branches because it motivates us to use the practice of continuous integration (we integrate our code into the main branch many times a day) rather than continuous isolation (in this practice you live very long in branches). However, most developers are used to seeing tests in their branches, so setting ENABLE_ISOLATION to true gives this result.

### Usage some parts of preset

Use parts of preset

```yaml
include:
  - project: "python-community/pypelines"
  - file: "templates/v1/deploy.yml"

deploy-prod-only:
  extends: .deploy-prod

gitlab-release-prod-only:
  extends: .gitlab-release
  variables:
    RELEASE_SERVER: production
```

Use rules and scripts by reference:

```yaml
include:
  - project: "python-community/pypelines"
    file: "_base/rules.yml "
  - project: "python-community/pypelines"
    file: "_base/jobs.yml "

notify-team-on-new-tag:
  before_script:
    - !reference [.default-docker-cli-job, before_script]
  script:
    - python -m <some notification app run>
  rules:
    - !reference [.default-rules, tag-rule]
```

### Creating complex tests

We assume to run simple tests in our presets. In case you need something more complex you can use a compose file. This file meant equally for local development and also it will be used in pipelines. To do so you need create file like this:

```yaml
#/docker-compose.yml
services:
  application: # this is standard name, you MUST define it like this
    build: # this section will be automatically removed by pypelines and replaced with image section
      context: .
    depends_on:
      - postgres
      - redis
      - rabbitmq
    restart: always
    volumes:
      - .:/srv/www/
    ports:
      - "8000:8000"

  # Remove unnecessary blocks or add images of systems used in your project
  postgres:
    image: $ARTIFACTORY_HOST/python-community-docker/techimage/postgres/postgres:15.2-alpine3.17
    environment:
      POSTGRES_DB: SOME_DB_NAME
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"

  redis:
    image: $ARTIFACTORY_HOST/python-community-docker/techimage/redis/redis:6.2.11-alpine3.17
    ports:
      - "6379:6379"
    environment:
      - ALLOW_EMPTY_PASSWORD=yes

  rabbitmq:
    image: $ARTIFACTORY_HOST/python-community-docker/techimage/rabbitmq/rabbitmq:3.11.13-management
    hostname: rabbitmq
    restart: always
    environment:
      - RABBITMQ_DEFAULT_USER=rmuser
      - RABBITMQ_DEFAULT_PASS=rmpassword
    ports:
      - 15672:15672
```

```yaml
# .gitlab-ci.yml
include:
  - project: "python-community/pypelines"
    file: "templates/v1/build.yml"

  - project: "python-community/pypelines"
    file: "_base/jobs.yml"

deploy-dev:
  extends: .deploy-dev

deploy-docker-compose:
  before_script:
    - !reference [.default-docker-cli-job, before_script]
  script:
    - docker compose run postgres
  needs:
    - deploy-dev
```

## Gitlab Integrations

Also this package gives integration with gitlab codequality(https://docs.gitlab.com/ee/ci/testing/code_quality.html) and container scanning(https://docs.gitlab.com/ee/user/application_security/container_scanning/).

Jobs with codequality reports support:

- `ruff`
- `mypy`
- `hadolint`

Jobs with container scanning report support:

- `trivy`

If you want to add any utility for static analyze or container scanning - check if it supports gitlab integration and may be integrated. To enable integration with gitlab you need to store report and pass it via artifacts:

```yaml
# for codequality(take in mind that report must be stored in this path)
artifacts:
  reports:
    codequality: $CODEQUALITY_REPORT

# for container scanning(take in mind that report must be stored in this path)
artifacts:
  reports:
    container_scanning: reports/$CONTAINER_SCANNING_REPORT
```

## Used utilities

Under the hood this pipeline uses those utilities.

| Utility         | Description                                             |
| --------------- | ------------------------------------------------------- |
| `Node`          | Frontend purposes                                       |
| `Docker`        | Run different images on the spot.                       |
| `Ruff`          | Lint and validate formatting of python code.            |
| `Mypy`          | Static analyzer for python code.                        |
| `Trivy`         | Vulnerability scanner for python code.                  |
| `Hadolint`      | Lint Dockerfiles for best practices.                    |
| `Kubescore`     | Lint kube manifests for best practices.                 |
| `Pygount`       | Count lines of code.                                    |
| `Anybadge`      | Adding lines of code badge.                             |
| `Kaniko`        | Build Docker images using Dockerfile.                   |
| `yq`            | Substitute to `docker-compose` files during test stage. |
| `Appscreener`   | Appsec scan image.                                      |
| `Sonar`         | Scan image.                                             |
| `Jfrog-cli`     | Set and check properties on images in the artifactory.  |
| `Skopeo`        | Copy images during release stage.                       |
| `Tiny Releaser` | Making releases in gitlab CI.                           |

## Environment variables

This pipeline has the following environment variables, which should be configured before first run:

**Note**: If the variable isn't set, corresponding stage will be skipped during pipeline execution. If required variable that used in multiple stages isn't set, whole pipeline may fail.

| Variable                                       | Required | Stage              | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------------------------- | -------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ARTIFACTORY_USER`                             | yes      | **multiple**       | Login for the service user, which will be used to push/pull artifacts to/from the Artifactory                                                                                                                                                                                                                                                                                                                                                                                                               |
| `ARTIFACTORY_PASSWORD`                         | yes      | **multiple**       | Password for the service user, which will be used to push/pull artifacts to/from the Artifactory                                                                                                                                                                                                                                                                                                                                                                                                            |
| `DOCKER_TEAM_REGISTRY_PREFIX`                  | yes      | **multiple**       | Docker team registry in the Artifactory for built Docker images                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `DEPLOY_HELM_CHART`                            | -        | **multiple**       | Directory for helm charts                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `PROJECT_SLUG`                                 | -        | **multiple**       | Must be set if you need to specify subdir of your project. <br>_Your project path:_ `root-group/child-group/grandchild-group/project-name`_<br>Without this var you will get path of artifactory REGISTRY as_ `$ARTIFACOTRY_HOST/$DOCKER_TEAM_REGISTRY_PREFIX/project-name/`_<br>But with_ `PROJECT_SLUG="/child-group/grandchild-group"`<br>_It would be:_ `$ARTIFACTORY_HOST/$DOCKER_TEAM_REGISTRY_PREFIX/child-group/grandchild-group/project-name/`<br> Note: Don't forget "/" at the start of the var! |
| `ENABLE_ISOLATION`                             | -        | **multiple**       | if set to "true", then build, test and scan jobs will be run on merge request event                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `NPMRC_ADDITIONAL_SCOPE`                       | -        | **multiple**       | With this variable you can add additional sections for the .npmrc file (dynamically created in CI/CD)                                                                                                                                                                                                                                                                                                                                                                                                       |
| `COREPACK_NPM_REGISTRY`                        | -        | **multiple**       | With this variable you can modify where corepack will search for package managers                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `NPM_INSTALL_EXTRA_ARGS`                       | -        | **multiple**       | Arguments for installing packages via npm                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `PNPM_INSTALL_EXTRA_ARGS`                      | -        | **multiple**       | Arguments for installing packages via pnpm                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `YARN_INSTALL_EXTRA_ARGS`                      | -        | **multiple**       | Arguments for installing packages via yarn                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `SEVERITY_COMMAND`                             | -        | **static-analyze** | Filter by severity for trivy (https://aquasecurity.github.io/trivy/v0.48/docs/configuration/filtering/#by-severity)                                                                                                                                                                                                                                                                                                                                                                                         |
| `CODEQUALITY_REPORT`                           | -        | **static-analyze** | File path for storing gitlab codequality report([about](#gitlab-integrations))                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `CONTAINER_SCANNING_REPORT`                    | -        | **static-analyze** | File path for storing gitlab container scanning report([about](#gitlab-integrations))                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `RUFF_VERSION`                                 | -        | **static-analyze** | Specify ruff version to use in pipeline                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `MYPY_VERSION`                                 | -        | **static-analyze** | Specify mypy version to use in pipeline                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `SECURITY_TEAM_ID`                             | -        | **appsec**         | If you want automatic AppSec in your pipeline, you must fill this with you team id.                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `SONAR_TOKEN`                                  | -        | **scan**           | Token for logging in Sonar (need to took from here: https://some.sonar.ru/)                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `SONAR_TEAM`                                   | -        | **scan**           | Sonar project for the team (should be presented here: https://some.sonar.ru/)                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `TEAM_PYPI_REPO`                               | -        | **publish**        | Pypi team name for package publishing. Required only in `presets/python-package--v1.yml` pipeline                                                                                                                                                                                                                                                                                                                                                                                                           |
| `DEPLOY_NAMESPACE` or `DEPLOY_NAMESPACE_<ENV>` | -        | **deploy**         | Namespace, where deploy should be performed. <br> It is possible to set one general variable for all available environments, or multiple different variables for specific environments. <br> ENV should be one of the following: dev, prev, prod.                                                                                                                                                                                                                                                           |
| `KUBE_CONTEXT` or `KUBE_CONTEXT_<ENV>`         | -        | **deploy**         | Gitlab agent for the namespace, where deploy should be performed. <br> It is possible to set one general variable for all available environments, or multiple different variables for specific environments. <br> ENV should be one of the following: dev, prev, prod.                                                                                                                                                                                                                                      |
| `ASSET_URL`                                    | -        | **deploy**         | Link to artifactory asset for tiny-releaser (https://gitlab.ru/python-community/pypi/tiny-releaser)                                                                                                                                                                                                                                                                                                                                                                                                         |
| `GENERIC_GITLAB_TOKEN`                         | -        | **gitlab-release** | Group or Project token, Maintainer role is required to create badges                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `E2E_PROJECT`                                  | -        | **e2e**            | Path to the repository, where E2E tests are presented                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

### Skiping some parts of pipeline

If you need to skip some jobs or stages you can use skipping variables.
The following variables must be set to True to skip some stages of this pipeline:

| Variable                   | Description                        |
| -------------------------- | ---------------------------------- | ------ |
| `SKIP_TRIVY`               | Skip trivy static analysis         |
| `SKIP_HADOLINT`            | Skip hadolint static analysis      |
| `SKIP_KUBESCORE`           | Skip kube score static analysis    |
| `SKIP_BUILD_ARM`           | Skip kaniko-build-arm stage        |
| `SKIP_TESTS`               | Skip tests execution               |
| `APPSEC_SKIP`              | Skip appsec stage                  |
| `SKIP_AUTO_SEMVER`         | Skip auto semver version bumping   |
| `SKIP_GITLAB_RELEASE`      | Skip of creating gitlab release    |
| `SKIP_RELEASE_PAGE_UPDATE` | Skip of updating releases infopage | !TO DO |

## Advanced

If you want to understand, what's going on under the hood - this section is right for you.
Here we will analyze how the backend preset works on the inside.

### Rules

In this pipeline we have a lot of different rules, because we wanted to be blazingly fast during our development process. You can see the full list of rules [here](_base/rules.yml). In this advanced section of the pipeline documentation, it will be marked when jobs from different stages are to be run.

The rules are exactly like this because motivation of this pipeline is to provide [continuous integration](https://www.atlassian.com/continuous-delivery/continuous-integration) and not [continuous isolation](https://devlead.io/DevTips/ContinuousIsolation) or [ci theatre](https://devlead.io/DevTips/CITheatre)

If you are a [continuous isolation](https://devlead.io/DevTips/ContinuousIsolation) enjoyer, then this pipeline has something special just for ya.
Behold! Continuous isolation mode, that can be easily enabled by setting ENABLE_ISOLATION variable to "true". This mode turned off by default.

### Frontend package managers

This pipeline supports usage of this package managers:

- [yarn](https://classic.yarnpkg.com/en/docs/install)
- [npm](https://docs.npmjs.com/getting-started/installing-node)
- [pnpm](https://pnpm.io/installation)

This functionality is provided by corepack(https://nodejs.org/api/corepack.html).
To use yarn or pnpm in pipelines(for local develop too) you need to specify `packageManager` in `package.json` file. How to do this you can read [here](https://github.com/nodejs/corepack?tab=readme-ov-file#usage).
If no package manager specified - npm will be used by default.

**Note**: If you want to use package manager in your jobs to install some packages or lint or smth else - you should extend `.configure-package-manager` job. Also prefered way to use $PACKAGE_MANAGER variable and not direct package manager name. So linting with this variable will look like this:

```bash
$PACKAGE_MANAGER run lint
```

For each package manager we have separate [variables](#environment-variables) for installing packages. You can also modify them for your needs.

### Type coverage support

For frontend packages we have support of type coverage badges.

To use this feature you should modify `lint-frontend` job to generate `svg` badge file. By default this file should have name , but you can change this by modifying `env` [TYPE_COVERAGE_BADGE](#environment-variables). You can use example below for using this feature for your project:

**Example:**

At first you need to configure `package.json` file to generate type coverage report.
We recommend you to use `type-coverage` package for this purpose:
https://github.com/plantain-00/type-coverage

Example uses `pnpm` package manager but you can use your own.

```json
"scripts": {
  "lint": "... && pnpm run lint:typecheck",
  "lint:typecheck": "pnpm dlx type-coverage | tee type-coverage.json",
},
```

Then you need to configure parameters for `type-coverage`. You can view all possible params here https://github.com/plantain-00/type-coverage?tab=readme-ov-file#arguments. You can do this in `package.json` or specify directly in `lint:typecheck`.

```json
"typeCoverage": {
  "project": "tsconfig.json",
  "is": 100,
  "detail": true,
  "strict": true,
  "reportSemanticError": true,
  "jsonOutput": true
},
```

Then you need generate badge from `type-coverage.json` report file in `lint-frontend` job. You can do this by modifying `.gitlab-ci.yml`:

```yaml
lint-frontend:
  extends: .lint-frontend
  script:
    - !reference [.lint-frontend, script]
    - ./type-coverage-badge.sh
```

You can use this script to generate badge or write your own:

```bash
if [ $# -eq 0 ]; then type_coverage_report='type-coverage.json'
else type_coverage_report=$1; fi

if ! [ -f $type_coverage_report ]; then
  echo "Can't build badge, because $type_coverage_report does not exist."
  exit 0
fi

type_coverage_percent=$(awk '/"percent":/ { print substr($2, 1, length($2)-1)}' $type_coverage_report)
int_type_coverage_percent=${type_coverage_percent%.*}

if [ $int_type_coverage_percent -eq 100 ]; then badge_color="green"
elif [ $int_type_coverage_percent -ge 90 ]; then badge_color="yellowgreen"
elif [ $int_type_coverage_percent -ge 70 ]; then badge_color="yellow"
elif [ $int_type_coverage_percent -ge 50 ]; then badge_color="orange"
else badge_color="red"; fi

npx badge-maker --label "type coverage" --message "$type_coverage_percent%" --color $badge_color > type-coverage-badge.svg
```

And then you need to add badge support for your repository([badges](#badges))

### Advanced stages

### static-analyze

Here we run the following code analysis tools.
Most of this tools are required, but some can be skipped with the flag.
For the required tools you will see "-" as the skip flag name.
In this table you can see:

- name of the tool
- name of the flag, that is responsible for this tool to be run or not
- presets, that using this tool

Jobs from this stage will be run `only on merge requests`.

| Tool                  | Flag           | Presets                    |
| --------------------- | -------------- | -------------------------- |
| `ruff`                | -              | Backend, Package           |
| `mypy`                | -              | Backend, Package           |
| `trivy`               | SKIP_TRIVY     | Backend, Package           |
| `hadolint`            | SKIP_HADOLINT  | Backend                    |
| `kube-score`          | SKIP_KUBESCORE | Backend                    |
| `lines-of-code-badge` | -              | Backend, Frontend, Package |
| `lint-frontend`       | -              | Frontend                   |

[Template](templates/v1/static-analyze.yml)

### build

At this stage image will be multiarch built and published to the artifactory, you have provided. All images and manifests will be stored in `ci` project folder. Unfortunately, none can be skipped out of the box at this stage. In this pipeline we are using `kaniko` because of it performance.

This is your artifactory project tree, after `build` stage has passed. Here `DOCKER_TEAM_REGISTRY_PREFIX`, `PROJECT_SLUG`, `CI_PROJECT_NAME` - names of variables, you have to set in advance.

```
DOCKER_TEAM_REGISTRY_PREFIX
└── PROJECT_SLUG
    └── CI_PROJECT_NAME
        └── ci
            ├── 027c3e98
            ├── 027c3e98-linux-amd64
            └── 027c3e98-linux-arm64
```

[Template](templates/v1/build.yml)

### test

This stage provides only one job `test-compose`, that can be skipped with the flag `SKIP_TESTS`. Job will launch a docker compose, that you have to provide. This job creates an artifact, that can be used to make a [coverage](#badges) badge.

After successful testing if commit is on `master/main/hotfix` branches, then "**tested**" property will be added to image.

[Template](templates/v1/test.yml)

### appsec

This stage provide application security scan via Appsec AppScreener.
Job need some environment variables to be set: [`APPSCREENER_TOKEN`](#environment-variables) and can be also skipped via [`APPSEC_SKIP`](#skip-variables).

[Template](templates/v1/appsec.yml)

### scan

Scanning is happening here, currently, there is only one tool: `SonarQube`. It can be skipped with the flag [`SKIP_SONAR`](#environment-variables).

After successful testing if commit is on `master/main/hotfix` branches, "**scanned**" property will be added to image.

[Template](templates/v1/scan.yml)

### publish

At this stage, job will publish project to Artifactory PyPi. This job will build project via `poetry build` for picked commit and then publish to team PyPi directory in Artifactory. You also need to specify team name [`TEAM_PYPI_REPO`](#environment-variables) for publishing.

[Template](templates/v1/publish.yml)

### image-release

This stage may consist of two jobs(`verify-artifactory-properties` and `image-release`).

1. If pipeline is runned on `master/main/hotfix` branches or if `CI_COMMIT_TAG` is specified for commit and is semver-like, we will have two jobs in stage. Job `verify-artifactory-properties` will will search image with **tested** and **scanned** properties. If no such image found - pipeline will fail. After this job `image-release` will try to copy image to the `release` project folder.

2. If pipeline is runned on merge requests with enabled isolation(ENABLE_ISOLATION), then stage will consist of only one manual job: `image-release`.

3. In other cases `image-release` stage will be empty.

Some words about work of `image-release` job:

Imagine, you create a new tag `1.0.0` with commit hash `027c3e98`.

You will have the following tree, after this stage pass.

```
DOCKER_TEAM_REGISTRY_PREFIX
└── PROJECT_SLUG
    └── CI_PROJECT_NAME
        ├── release
        │   └── 1.0.0
        └── ci
            ├── 027c3e98
            ├── 027c3e98-linux-amd64
            └── 027c3e98-linux-arm64
```

This is not the only use-case. Images will be released even without tags then name of the release will be `CI_COMMIT_SHORT_SHA`.

```
DOCKER_TEAM_REGISTRY_PREFIX
└── PROJECT_SLUG
    └── CI_PROJECT_NAME
        ├── release
        │   └── 027c3e98
        └── ci
            ├── 027c3e98
            ├── 027c3e98-linux-amd64
            └── 027c3e98-linux-arm64
```

[Template](templates/v1/image-release.yml)

### deploy

This stage contains different jobs, that uses different gitlab environments. For example, to deploy to `prod` you should define a `KUBE_CONTEXT` and `DEPLOY_NAMESPACE` in your environment, or you can set `KUBE_CONTEXT_PROD` and `DEPLOY_NAMESPACE_PROD` globally.

Here we also use artifactory properties, to ignore certain artifacts during [cleanup process](https://gitlab.ru/python-community/pypi/arti-cleaner). After deploy on `prod` was successful, `release-prod` property will be unset from all images inside `release` folder and than set to the image that was just released.

Rules for this stage are pretty complex, so please, see it yourself [here](_base/rules.yml#L18).

In isolation mode, auto semver job will be triggered after merging to default branch, which bumps version and creates a new tag

After deploy the following environment variables are passed to containers:

- CI_COMMIT_TAG - commit tag if exists
- CI_COMMIT_SHA - commit hash
- CI_COMMIT_REF_NAME - branch name
- CI_PROJECT_NAME - gitlab repo name

[Template](templates/v1/deploy.yml)

### gitlab-release

This stage will automatically create a new gitlab release and put a link to the released artifact. Is also creates a release [badge](#badges), that clearly indicates release version. Jobs require `GENERIC_GITLAB_TOKEN` with write rules for badge and release creation. There are two jobs here, you can skip all of them. [Rules](_base/rules.yml#L30) are not so obvious and requires some attention.

| Job                          | Flag                                            |
| ---------------------------- | ----------------------------------------------- |
| `gitlab-release`             | SKIP_GITLAB_RELEASE                             |
| `gitlab-release-update-prod` | SKIP_GITLAB_RELEASE or SKIP_RELEASE_PAGE_UPDATE |

[Template](templates/v1/gitlab-release.yml)

### e2e

Here [downstream pipeline](https://docs.gitlab.com/ee/ci/pipelines/downstream_pipelines.html) technique is used. You have to provide `E2E_PROJECT` to run the pipeline there.
Jobs will be run if `E2E_PROJECT` is provided and `CI_COMMIT_TAG` is semver-like.

[Template](templates/v1/e2e.yml)

<b>P.S.</b><br>
If you feel like you misunderstood something, feel free to read the [source code](https://gitlab.ru/python-community/pypelines). There's a small description nearby every job, that will help you to understand the behavior and requirements.

## Badges

If you are using one of presets, or inherited from some jobs, you can add badges to your
project. Here `job name` - is the one, that provides some artifact after its execution, that can be used in badges. If there is no `job name`, then you can add badge without using any job.

| Job name                             | Badge                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------- |
| `.lint-frontend`                     | ![](https://img.shields.io/static/v1?label=type%20coverage&message=100%&color=green)        |
| `.lines-of-code-badge`               | ![](https://img.shields.io/static/v1?label=lines%20of%20code&message=100&color=brightgreen) |
| `.test-python-ci`/`.test-compose-ci` | ![](https://img.shields.io/static/v1?label=coverage&message=100%&color=brightgreen)         |
| `.gitlab-release`                    | ![](https://img.shields.io/static/v1?label=preview%20version&message=1.0.0&color=blue)      |
| if you use static analyze jobs       | ![](https://img.shields.io/badge/code%20style-python%20community%202023-blue)               |

## FAQ

- **Why do we use docker compose in tests?**
  Docker compose is very flexible, so you can decide which services do you need in your particular case. Also, we cant hard-code `services` for any imaginable dependency in the world.
