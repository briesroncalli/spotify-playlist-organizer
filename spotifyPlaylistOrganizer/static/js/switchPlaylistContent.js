function switchPlaylistContent(id, selection) {
    var playlistDiv = document.getElementById(id);
    var tracksDiv = playlistDiv.getElementsByClassName("tracks")[0];
    var statsDiv = playlistDiv.getElementsByClassName("stats")[0];
    var buttons = playlistDiv.getElementsByClassName("switch-content");
    var clickedButton = buttons[selection]
    var unclickedButton = buttons[selection == 0 ? 1 : 0]
    var repeatClick = clickedButton.classList.contains('selected')
    if (repeatClick) {
        return
    }
    clickedButton.classList.add('selected')
    unclickedButton.classList.remove('selected')
    if (clickedButton.classList.contains('songs')) {
        tracksDiv.classList.remove('hidden')
        statsDiv.classList.add('hidden')
    } else if (clickedButton.classList.contains('data')) {
        statsDiv.setAttribute("style","height:" + (playlistDiv.offsetHeight - 136) + "px")
        // statsDiv.setAttribute("style","width:" + (tracksDiv.offsetwidth - 20) + "px")
        statsDiv.classList.remove('hidden')
        tracksDiv.classList.add('hidden')
    }
}
