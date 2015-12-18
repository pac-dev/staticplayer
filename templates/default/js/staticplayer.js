// on page loaded
$(function() {
	// generate player
	var a = audiojs.createAll({
		preload: false,
		loadError: function(e) {
			$(this.wrapper).removeClass("loading");
			$(this.wrapper).addClass("error");
			$(".error-message").html('Error loading track');
		},
		trackEnded: function() {
			if (playingTracks[trackNumber+1]) {
				trackNumber++
				playTrack()
			} else if (loopingAll) {
				trackNumber = 0
				playTrack()
			} else
				updatePlayingClasses()
		},
		play: function() {
			var player = this.settings.createPlayer;
			audiojs.helpers.addClass(this.wrapper, player.playingClass);
			updatePlayingClasses()
		},
		pause: function() {
			var player = this.settings.createPlayer;
			audiojs.helpers.removeClass(this.wrapper, player.playingClass);
			updatePlayingClasses()
		},
	})
	audio = a[0]
	function setPlayerText(text) {
		$(".audiojs .progress").html(text)
		$(".audiojs .undertext").html(text)
	}
	function playTrack() {
		// monkeypatch audiojs bug (fixed?)
		if (!(trackNumber in playingTracks)) {
			audio.pause()
			setPlayerText("&nbsp;&nbsp;experimental player audio.js")
			return
		}
		$(".audiojs").addClass("loading");
		$(".audiojs").removeClass("error");
		audio.load(playingTracks[trackNumber].url)
		audio.play()
		setPlayerText("&nbsp;&nbsp;" + playingTracks[trackNumber].title + " - " + playingTracks[trackNumber].artist)
	}
	
	// generate volume bars
	var volHeight = 16, volWidth=56, volSteps = 8
	var barWidth = Math.floor(volWidth / volSteps)
	$(".audiojs .time").after('<div class="volume"></div>')
	$(".audiojs .loaded").after('<div class="undertext"></div>')
	$(".audiojs .volume").css("width", volWidth)
	for (var s=0; s<volSteps; s++) {
		var barHeight = Math.floor((volHeight / volSteps) * (s+1))
		var barLeft = Math.floor((volWidth / volSteps) * s)
		var barVol = (1.0 / (volSteps-1)) * s
		var displayVol = "Volume: " + Math.floor(barVol*100) + "%"
		barVol = barVol*barVol // better curve
		$(".audiojs .volume").append(
			'<div class="vol-bar-back" title="' +
			displayVol + '" data-volume="' +
			barVol + '" style="height:' +
			volHeight + 'px;left:' +
			barLeft + 'px;width:' +
			barWidth + 'px"><div class="vol-fill" style="height:' +
			barHeight + 'px;"></div></div>'
		)
	}
	$(".vol-bar-back").click(function(){
		currentVolume = $(this).attr('data-volume')
		audio.setVolume(currentVolume)
		updateVolumeDisplay()
	})
	function updateVolumeDisplay() {
		$(".vol-bar-back").each(function(index, ele) {
			if ($(ele).attr("data-volume")<=currentVolume)
				$(ele).children().addClass("vol-fill-on")
			else
				$(ele).children().removeClass("vol-fill-on")
		})
	}
	currentVolume = 0.52
	audio.setVolume(currentVolume)
	updateVolumeDisplay()
	
	// generate extra buttons
	$(".audiojs .play-pause").before(
		'<div class="extra_button previous"></div>');
	$(".audiojs .play-pause").after(
		'<div class="extra_button next"></div>' + 
		'<div class="extra_button loopall" title="loop playlist"></div>');
	$(".audiojs .previous").click(function(){
		if (playingTracks[trackNumber-1]) {
			trackNumber--
			playTrack()
		}
	})
	$(".audiojs .next").click(function(){
		if (playingTracks[trackNumber+1]) {
			trackNumber++
			playTrack()
		}
	})
	$(".audiojs .loopall").click(function(){
		loopingAll = !loopingAll
		$(".audiojs .loopall").toggleClass("looping", loopingAll)
	})
	
	
	// playlist menu
	playlists_visible = false
	$("#playlist_dropper").click(function(){
		playlists_visible = !playlists_visible
		$("#playlist_menu").toggle(playlists_visible)
		$("#playlist_dropper").toggleClass("flipped", playlists_visible)
	})
		$("#playlist_menu").toggle(playlists_visible)
		$("#playlist_dropper").toggleClass("flipped", playlists_visible)
		
	
	// tracklist
	updatePlayingClasses = function () {
		$('.track_item').removeClass('playing_track')
		if (audio.playing)
			$('.track_item').eq(trackNumber).addClass('playing_track')
	}
	trackNumber = 0
	$('.track_item').click(function (e) {
		e.preventDefault()
		trackNumber = Number($(this).attr('data-index'))
		playTrack()
		return false
	})
	updatePlayingClasses()
	
	loopingAll = false
	playTrack()
	audio.pause()
	
	// less stupid hover that doesn't stick when touch-scrolling
	$('.hoverable').on('touchstart mouseenter', function(e) {
		$(this).addClass('hover');
	}).on('touchmove mouseleave click', function(e) {
		$(this).removeClass('hover');
	});
})

window.onunload = function(){};
