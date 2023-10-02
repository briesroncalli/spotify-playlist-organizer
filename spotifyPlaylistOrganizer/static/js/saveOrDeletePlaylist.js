function saveOrDeletePlaylist(id, songs, name) {
    var saveButton = document.getElementsByClassName("save-playlist")[id-1];
    var buttonIcon = saveButton.getElementsByTagName("i")[0]
    var buttonLabel = saveButton.getElementsByTagName("p")[0]
    var requestData = {
        name: name,
        songs: songs
    };

    if (saveButton.classList.contains("saved")) {
        // remove saved playlist & switch button class + content
        if (sendDeleteRequest(requestData)) {
            saveButton.classList.remove("saved")
            buttonIcon.classList.remove("fa-check")
            buttonIcon.classList.add("fa-plus")
            buttonLabel.textContent = "Save Playlist"
        }
    } else {
        // save playlist & switch button class + content
        if (sendSaveRequest(requestData)) {
            saveButton.classList.add("saved")
            buttonIcon.classList.remove("fa-plus")
            buttonIcon.classList.add("fa-check")
            buttonLabel.textContent = "Saved!"
        }
    }
}

function sendSaveRequest(data) {
    var success = false;
    $.ajax({
        url: '/savePlaylist',
        type: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        async: false,
        success: function (response) {
            console.log(response);
            success = true;
        },
        error: function (error) {
            console.log(error);
        }
    });
    return success;
}

function sendDeleteRequest(requestData) {
    var success = false;
    $.ajax({
        url: '/deletePlaylist',
        type: 'POST',
        data: JSON.stringify(requestData),
        contentType: 'application/json',
        async: false,
        success: function (response) {
            console.log(response);
            success = true;
        },
        error: function (error) {
            console.log(error);
        }
    });
    return success;
}
