$(document).ready(function() {
    var audio = new Audio();
  
    // Attach click event listeners to all elements with the class 'play-pause-button'
    $('.play-pause-button').on("click", function() {
      var preview_url = $(this).data('argument');
      
      // Pause any currently playing audio
      audio.pause();
      
      if ($(this).hasClass('fa-play')) {
        audio = new Audio(preview_url);
        $(this).removeClass('fa-play');
        $(this).addClass('fa-pause');
        audio.play();
      } else {
        $(this).removeClass('fa-pause');
        $(this).addClass('fa-play');
        audio.pause();
      }
    });
  
    audio.onended = function() {
      // Reset all elements with the class 'play-pause-button' to play icon when audio ends
      $('.play-pause-button').removeClass('fa-pause');
      $('.play-pause-button').addClass('fa-play');
    };
});
