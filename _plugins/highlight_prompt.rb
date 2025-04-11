require 'cgi'

Jekyll::Hooks.register [:documents], :pre_render do |doc|
  puts "Prompt highlight plugin loaded!"
  doc.content.gsub!(/```\n(.*?)```/m) do |_match|
    block = $1
    lines = block.lines.map(&:chomp)

    result = []
    output_buffer = []

    lines.each do |line|
      if line.strip.start_with?('$')
        # Flush the output buffer first
        unless output_buffer.empty?
          result << "<div>#{CGI.escapeHTML(output_buffer.join("\n"))}</div>"
          output_buffer.clear
        end

        # Extract command without the $
        command = line.strip.sub(/^\$\s?/, '')
        result << "<div class=\"cmd-line\"><span class=\"prompt\">$</span> #{CGI.escapeHTML(command)}</div>"
      else
        output_buffer << line
      end
    end

    # Flush any remaining output
    unless output_buffer.empty?
      result << "<div>#{CGI.escapeHTML(output_buffer.join("\n"))}</div>"
    end

    "<div class=\"terminal-block\">\n#{result.join("\n")}\n</div>"
  end
end
