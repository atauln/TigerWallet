<div align="center" id="top"> 
  <img src="./static/icons/icon-dark.png" alt="Tigerwallet" width="200px" height="200px" />

  &#xa0;

  <!-- <a href="https://tigerwallet.netlify.app">Demo</a> -->
</div>

<h1 align="center">TigerWallet</h1>

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/atauln/tigerwallet?color=56BEB8">

  <img alt="Github language count" src="https://img.shields.io/github/languages/count/atauln/tigerwallet?color=56BEB8">

  <img alt="Repository size" src="https://img.shields.io/github/repo-size/atauln/tigerwallet?color=56BEB8">

  <img alt="License" src="https://img.shields.io/github/license/atauln/tigerwallet?color=56BEB8">

  <!-- <img alt="Github issues" src="https://img.shields.io/github/issues/atauln/tigerwallet?color=56BEB8" /> -->

  <!-- <img alt="Github forks" src="https://img.shields.io/github/forks/atauln/tigerwallet?color=56BEB8" /> -->

  <!-- <img alt="Github stars" src="https://img.shields.io/github/stars/atauln/tigerwallet?color=56BEB8" /> -->
</p>

<!-- Status -->

<!-- <h4 align="center"> 
	🚧  Tigerwallet 🚀 Under construction...  🚧
</h4> 

<hr> -->

<p align="center">
  <a href="#dart-about">About</a> &#xa0; | &#xa0; 
  <a href="#sparkles-features">Features</a> &#xa0; | &#xa0;
  <a href="#rocket-technologies">Technologies</a> &#xa0; | &#xa0;
  <a href="#white_check_mark-requirements">Requirements</a> &#xa0; | &#xa0;
  <a href="#checkered_flag-starting">Starting</a> &#xa0; | &#xa0;
  <a href="#memo-license">License</a> &#xa0; | &#xa0;
  <a href="https://github.com/atauln" target="_blank">Author</a>
</p>

<br>

## :dart: About ##

This project utilizes RIT's TigerSpend API to receive purchase information for users and display it in a user-friendly manner.

## :sparkles: Features ##

:heavy_check_mark: Overall Balance\
:heavy_check_mark: Budgeting\
:heavy_check_mark: Account detection and switching\
:heavy_check_mark: Purchase history

## To be implemented: ##
:x: Notifications\
:x: Balance warnings\
:x: Balance predictions\
:x: Restaraunt traffic\
:x: Restaraunt map\
:x: Travelling chefs\
:x: CSH pings with SSO

## :rocket: Technologies ##

The following tools were used in this project:

- [Flask](https://flask.palletsprojects.com/en/2.2.x/)
- [Python](https://www.python.org/)
- [Bootstrap](https://getbootstrap.com/)
- [Docker](https://www.docker.com/)
- [Podman](https://podman.io/)

## :white_check_mark: Requirements ##

Before starting :checkered_flag:, you need to have [Git](https://git-scm.com) and [Podman](https://podman.io/) installed.

## :checkered_flag: Starting ##

```bash
# Clone this project
$ git clone https://github.com/atauln/tigerwallet

# Access
$ cd tigerwallet

# Build image
$ podman build . -t latest

# Run the container
$ podman run latest

# The server will initialize in the <http://localhost:8080>
```

## :memo: License ##

This project is under license from GNU. For more details, see the [LICENSE](LICENSE) file.


Made with :heart: by <a href="https://github.com/atauln" target="_blank">Ata Noor</a>\
(Please don't sue me RIT)


<a href="#top">Back to top</a>
